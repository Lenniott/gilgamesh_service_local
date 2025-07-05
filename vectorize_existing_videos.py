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
        Vectorize a single video by creating individual vectors for each transcript segment and scene description.
        
        Args:
            video: Video record from database
            
        Returns:
            True if successful, False otherwise
        """
        video_id = video["id"]
        carousel_index = video.get("carousel_index", 0)
        
        try:
            # Ensure collections exist
            transcript_collection = "video_transcript_segments"
            scene_collection = "video_scene_descriptions"
            await self.connections.ensure_collection_exists(transcript_collection)
            await self.connections.ensure_collection_exists(scene_collection)
            
            vectors_created = 0
            vector_ids = []
            
            # Process transcript segments individually
            if video.get("transcript"):
                transcript_data = video["transcript"]
                if isinstance(transcript_data, str):
                    try:
                        transcript_data = json.loads(transcript_data)
                    except json.JSONDecodeError:
                        transcript_data = []
                
                if isinstance(transcript_data, list):
                    for segment_index, segment in enumerate(transcript_data):
                        if isinstance(segment, dict):
                            text = segment.get('text', '')
                            if text:
                                # Generate embedding for this segment only
                                embedding = await self.connections.generate_embedding(text)
                                if embedding:
                                    # Create vector ID for this segment (must be UUID)
                                    import uuid
                                    vector_id = str(uuid.uuid4())
                                    
                                    # Prepare metadata for this transcript segment
                                    segment_metadata = {
                                        "video_id": video_id,
                                        "segment_index": segment_index,
                                        "text": text,
                                        "start": segment.get('start', 0),
                                        "end": segment.get('end', 0),
                                        "duration": segment.get('duration', 0),
                                        "url": video["url"],
                                        "carousel_index": carousel_index,
                                        "type": "transcript_segment",
                                        "tags": [],  # Individual segments don't have tags
                                        "created_at": str(video["created_at"]),
                                        "vectorized_at": str(datetime.now())
                                    }
                                    
                                    # Store transcript segment vector
                                    success = await self.connections.store_vector(
                                        collection_name=transcript_collection,
                                        vector_id=vector_id,
                                        embedding=embedding,
                                        metadata=segment_metadata
                                    )
                                    
                                    if success:
                                        vectors_created += 1
                                        vector_ids.append(vector_id)
                                        logger.debug(f"✅ Created transcript segment vector {segment_index} for video {video_id}")
                                    else:
                                        logger.warning(f"⚠️ Failed to store transcript segment {segment_index} for video {video_id}")
            
            # Process scene descriptions individually  
            if video.get("descriptions"):
                descriptions_data = video["descriptions"]
                if isinstance(descriptions_data, str):
                    try:
                        descriptions_data = json.loads(descriptions_data)
                    except json.JSONDecodeError:
                        descriptions_data = []
                
                if isinstance(descriptions_data, list):
                    for scene_index, scene in enumerate(descriptions_data):
                        if isinstance(scene, dict):
                            # Try both field names for backward compatibility
                            desc = scene.get('ai_description', '') or scene.get('description', '')
                            if desc:
                                # Generate embedding for this scene only
                                embedding = await self.connections.generate_embedding(desc)
                                if embedding:
                                    # Create vector ID for this scene (must be UUID)
                                    import uuid
                                    vector_id = str(uuid.uuid4())
                                    
                                    # Prepare metadata for this scene description
                                    scene_metadata = {
                                        "video_id": video_id,
                                        "scene_index": scene_index,
                                        "description": desc,
                                        "start_time": scene.get('start_time', 0),
                                        "end_time": scene.get('end_time', 0),
                                        "duration": scene.get('duration', 0),
                                        "frame_count": scene.get('frame_count', 0),
                                        "url": video["url"],
                                        "carousel_index": carousel_index,
                                        "type": "scene_description",
                                        "tags": scene.get('ai_tags', []) or scene.get('tags', []),
                                        "created_at": str(video["created_at"]),
                                        "vectorized_at": str(datetime.now())
                                    }
                                    
                                    # Store scene description vector
                                    success = await self.connections.store_vector(
                                        collection_name=scene_collection,
                                        vector_id=vector_id,
                                        embedding=embedding,
                                        metadata=scene_metadata
                                    )
                                    
                                    if success:
                                        vectors_created += 1
                                        vector_ids.append(vector_id)
                                        logger.debug(f"✅ Created scene description vector {scene_index} for video {video_id}")
                                    else:
                                        logger.warning(f"⚠️ Failed to store scene description {scene_index} for video {video_id}")
            
            # Check if we created any vectors
            if vectors_created == 0:
                logger.warning(f"⚠️ No vectors created for video {video_id} - no valid content found")
                return False
            
            # Update PostgreSQL with vectorization info (store count instead of single ID)
            # We'll need to update the database method to handle multiple vectors
            await self.db.update_vectorization_status(video_id, f"{vectors_created}_vectors", "text-embedding-3-small")
            logger.info(f"✅ Successfully vectorized video {video_id} (carousel {carousel_index}): {vectors_created} vectors created")
            return True
                
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
        if self.db and self.db.connections:
            await self.db.connections.close_all()

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