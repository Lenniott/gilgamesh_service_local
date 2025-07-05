#!/usr/bin/env python3
"""
Vectorize Existing Videos Script

This script finds all videos in the PostgreSQL database that haven't been vectorized yet
and processes them to add vector embeddings to Qdrant.

Usage:
    python vectorize_existing_videos.py [--limit N] [--dry-run]

Options:
    --limit N    : Only process N videos (default: no limit)
    --dry-run    : Show what would be processed without actually doing it
    --verbose    : Show detailed logging
"""

import asyncio
import argparse
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

# Import our database and connection classes
from app.simple_db_operations import SimpleVideoDatabase
from app.db_connections import DatabaseConnections

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VectorizeExistingVideos:
    """Class to handle vectorizing existing videos that haven't been vectorized."""
    
    def __init__(self):
        self.db = None
        self.connections = None
        
    async def initialize(self):
        """Initialize database connections."""
        try:
            self.db = SimpleVideoDatabase()
            await self.db.initialize()
            self.connections = self.db.connections
            
            # Verify we have required connections
            if not self.connections:
                raise Exception("Database connections not available")
            if not self.connections.qdrant_client:
                raise Exception("Qdrant client not available - check QDRANT_URL and QDRANT_API_KEY")
            if not self.connections.openai_client:
                raise Exception("OpenAI client not available - check OPENAI_API_KEY")
                
            logger.info("✅ Database connections initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize database connections: {e}")
            raise
            
    async def get_unvectorized_videos(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all videos that haven't been vectorized yet.
        
        Args:
            limit: Maximum number of videos to return
            
        Returns:
            List of video records that need vectorization
        """
        try:
            conn = await self.connections.pg_pool.acquire()
            try:
                query = """
                SELECT id, url, carousel_index, transcript, descriptions, tags, created_at
                FROM simple_videos 
                WHERE vectorized_at IS NULL 
                AND (transcript IS NOT NULL OR descriptions IS NOT NULL)
                ORDER BY created_at DESC
                """
                
                if limit:
                    query += f" LIMIT {limit}"
                
                rows = await conn.fetch(query)
                
                videos = []
                for row in rows:
                    video_data = {
                        "id": row["id"],
                        "url": row["url"],
                        "carousel_index": row["carousel_index"],
                        "transcript": row["transcript"],
                        "descriptions": row["descriptions"],
                        "tags": row["tags"],
                        "created_at": row["created_at"]
                    }
                    videos.append(video_data)
                
                logger.info(f"📊 Found {len(videos)} videos that need vectorization")
                return videos
                
            finally:
                await self.connections.pg_pool.release(conn)
                
        except Exception as e:
            logger.error(f"❌ Failed to get unvectorized videos: {e}")
            return []
    
    async def vectorize_video(self, video: Dict[str, Any]) -> bool:
        """
        Vectorize a single video and update the database.
        
        Args:
            video: Video record from database
            
        Returns:
            True if successful, False otherwise
        """
        video_id = video["id"]
        carousel_index = video.get("carousel_index", 0)
        
        try:
            # Ensure collection exists
            collection_name = "video_transcripts"
            await self.connections.ensure_collection_exists(collection_name)
            
            # Create text content for embedding
            text_content = []
            
            # Add transcript content
            if video.get("transcript"):
                transcript_data = video["transcript"]
                if isinstance(transcript_data, str):
                    try:
                        transcript_data = json.loads(transcript_data)
                    except json.JSONDecodeError:
                        transcript_data = transcript_data  # Keep as string
                
                if isinstance(transcript_data, list):
                    for segment in transcript_data:
                        if isinstance(segment, dict):
                            text_content.append(segment.get('text', ''))
                        else:
                            text_content.append(str(segment))
                else:
                    text_content.append(str(transcript_data))
            
            # Add scene descriptions
            if video.get("descriptions"):
                descriptions_data = video["descriptions"]
                if isinstance(descriptions_data, str):
                    try:
                        descriptions_data = json.loads(descriptions_data)
                    except json.JSONDecodeError:
                        descriptions_data = []
                
                if isinstance(descriptions_data, list):
                    for scene in descriptions_data:
                        if isinstance(scene, dict):
                            # Try both field names for backward compatibility
                            desc = scene.get('ai_description', '') or scene.get('description', '')
                            if desc:
                                text_content.append(desc)
            
            # Check if we have text content
            if not text_content:
                logger.warning(f"⚠️ No text content found for video {video_id} - skipping")
                return False
            
            # Combine all text for embedding
            combined_text = " ".join(text_content)
            
            # Generate embedding
            embedding = await self.connections.generate_embedding(combined_text)
            if not embedding:
                logger.error(f"❌ Failed to generate embedding for video {video_id}")
                return False
            
            # Extract tags
            all_tags = set()
            if video.get("tags"):
                tags_data = video["tags"]
                if isinstance(tags_data, str):
                    try:
                        tags_data = json.loads(tags_data)
                    except json.JSONDecodeError:
                        tags_data = []
                
                if isinstance(tags_data, list):
                    all_tags.update(tags_data)
            
            # Prepare metadata for Qdrant
            qdrant_metadata = {
                "video_id": video_id,
                "url": video["url"],
                "carousel_index": carousel_index,
                "has_transcript": bool(video.get("transcript")),
                "has_scenes": bool(video.get("descriptions")),
                "tags": list(all_tags),
                "text_content": combined_text[:1000],  # Truncate for storage
                "created_at": str(video["created_at"]),
                "vectorized_at": str(datetime.now())
            }
            
            # Store in Qdrant (use UUID for vector ID)
            import uuid
            vector_id = str(uuid.uuid4())
            success = await self.connections.store_vector(
                collection_name=collection_name,
                vector_id=vector_id,
                embedding=embedding,
                metadata=qdrant_metadata
            )
            
            if success:
                # Update PostgreSQL with vectorization info
                await self.db.update_vectorization_status(video_id, vector_id, "text-embedding-3-small")
                logger.info(f"✅ Successfully vectorized video {video_id} (carousel {carousel_index})")
                return True
            else:
                logger.error(f"❌ Failed to store vector for video {video_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error vectorizing video {video_id}: {e}")
            return False
    
    async def vectorize_all_unvectorized(self, limit: Optional[int] = None, dry_run: bool = False) -> Dict[str, Any]:
        """
        Vectorize all unvectorized videos.
        
        Args:
            limit: Maximum number of videos to process
            dry_run: If True, only show what would be processed
            
        Returns:
            Summary of the vectorization process
        """
        try:
            # Get unvectorized videos
            videos = await self.get_unvectorized_videos(limit)
            
            if not videos:
                logger.info("🎉 No videos need vectorization - all caught up!")
                return {
                    "success": True,
                    "message": "No videos need vectorization",
                    "total_videos": 0,
                    "processed": 0,
                    "successful": 0,
                    "failed": 0
                }
            
            if dry_run:
                logger.info(f"🔍 DRY RUN: Would process {len(videos)} videos")
                for i, video in enumerate(videos, 1):
                    logger.info(f"  {i}. Video {video['id']} (carousel {video.get('carousel_index', 0)}) - {video['url']}")
                
                return {
                    "success": True,
                    "message": f"DRY RUN: Would process {len(videos)} videos",
                    "total_videos": len(videos),
                    "processed": 0,
                    "successful": 0,
                    "failed": 0,
                    "videos": videos
                }
            
            # Process videos
            logger.info(f"🚀 Starting vectorization of {len(videos)} videos...")
            
            successful = 0
            failed = 0
            
            for i, video in enumerate(videos, 1):
                logger.info(f"📹 Processing video {i}/{len(videos)}: {video['id']}")
                
                success = await self.vectorize_video(video)
                if success:
                    successful += 1
                else:
                    failed += 1
                
                # Progress update every 10 videos
                if i % 10 == 0:
                    logger.info(f"📊 Progress: {i}/{len(videos)} videos processed ({successful} successful, {failed} failed)")
            
            # Final summary
            logger.info(f"🎉 Vectorization complete!")
            logger.info(f"📊 Total: {len(videos)} videos")
            logger.info(f"✅ Successful: {successful}")
            logger.info(f"❌ Failed: {failed}")
            
            return {
                "success": True,
                "message": f"Vectorization complete: {successful}/{len(videos)} successful",
                "total_videos": len(videos),
                "processed": len(videos),
                "successful": successful,
                "failed": failed
            }
            
        except Exception as e:
            logger.error(f"❌ Vectorization process failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def cleanup(self):
        """Clean up database connections."""
        if self.db:
            await self.db.cleanup()

async def main():
    """Main function to run the vectorization script."""
    parser = argparse.ArgumentParser(description="Vectorize existing videos that haven't been vectorized yet")
    parser.add_argument("--limit", type=int, help="Maximum number of videos to process")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without actually doing it")
    parser.add_argument("--verbose", action="store_true", help="Show detailed logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    vectorizer = VectorizeExistingVideos()
    
    try:
        # Initialize
        await vectorizer.initialize()
        
        # Run vectorization
        result = await vectorizer.vectorize_all_unvectorized(
            limit=args.limit,
            dry_run=args.dry_run
        )
        
        # Print final result
        print("\n" + "="*50)
        print("VECTORIZATION SUMMARY")
        print("="*50)
        print(f"Success: {result['success']}")
        print(f"Message: {result['message']}")
        if result.get('total_videos'):
            print(f"Total videos: {result['total_videos']}")
            print(f"Processed: {result['processed']}")
            print(f"Successful: {result['successful']}")
            print(f"Failed: {result['failed']}")
        print("="*50)
        
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        print(f"\n❌ Error: {e}")
        
    finally:
        await vectorizer.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 