#!/usr/bin/env python3
"""
Simplified Database Operations using single table approach
Much cleaner and easier to manage than multi-table complexity
"""

import os
import json
import uuid
import logging
import base64
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.db_connections import get_db_connections, DatabaseConnections

logger = logging.getLogger(__name__)

class SimpleVideoDatabase:
    """
    Simplified database operations for video storage.
    Single table approach with carousel support - much cleaner than complex multi-table design.
    """
    
    def __init__(self):
        self.connections = None
    
    async def initialize(self):
        """Initialize database connections."""
        try:
            self.connections = DatabaseConnections()
            await self.connections.connect_all()
            return await self._ensure_connection()
        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {e}")
            return False
    
    async def _ensure_connection(self):
        """Ensure database connection is available."""
        if not self.connections:
            return False
        
        # Test if we have a working PostgreSQL connection
        return bool(self.connections.pg_pool)
    
    async def save_video_carousel(self, video_path: str, url: str, carousel_index: int = 0,
                        transcript_data: Optional[List[Dict]] = None,
                        scenes_data: Optional[List[Dict]] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Save video with carousel support to simple_videos table.
        
        Args:
            video_path: Path to video file
            url: Normalized URL (without img_index)
            carousel_index: Index in carousel (0 for single videos)
            transcript_data: Optional transcript segments
            scenes_data: Optional scene descriptions
            metadata: Optional additional metadata
            
        Returns:
            Video ID if successful, None if failed
        """
        if not await self._ensure_connection():
            logger.error("❌ Database connection not available")
            return None
        
        try:
            # Read and encode video
            with open(video_path, 'rb') as f:
                video_content = f.read()
                video_base64 = base64.b64encode(video_content).decode('utf-8')
            
            # Prepare data
            transcript_json = json.dumps(transcript_data) if transcript_data else None
            
            # Extract descriptions and tags from scenes
            descriptions = []
            all_tags = set()
            
            if scenes_data:
                for scene in scenes_data:
                    description_obj = {
                        "start_time": scene.get("start_time"),
                        "end_time": scene.get("end_time"),
                        "description": scene.get("ai_description", ""),
                        "analysis_success": scene.get("analysis_success", False)
                    }
                    
                    # Include transcript context if available
                    if scene.get("has_transcript"):
                        description_obj["has_transcript"] = True
                        description_obj["scene_transcript"] = scene.get("scene_transcript")
                    
                    descriptions.append(description_obj)
                    
                    # Collect tags
                    scene_tags = scene.get("ai_tags", [])
                    all_tags.update(scene_tags)
            
            descriptions_json = json.dumps(descriptions) if descriptions else None
            tags_array = list(all_tags) if all_tags else None
            
            # Convert metadata to JSON string if it's a dict
            metadata_json = json.dumps(metadata) if metadata else None
            
            # Get fresh connection and insert
            conn = await self.connections.pg_pool.acquire()
            try:
                video_id = str(uuid.uuid4())
                
                insert_query = """
                INSERT INTO simple_videos (
                    id, url, carousel_index, video_base64, transcript, descriptions, tags, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id;
                """
                
                result = await conn.fetchrow(
                    insert_query,
                    video_id,
                    url,
                    carousel_index,
                    video_base64,
                    transcript_json,
                    descriptions_json,
                    tags_array,
                    metadata_json
                )
                
                if result:
                    logger.info(f"✅ Video saved to database: {video_id} (carousel_index: {carousel_index})")
                    return str(result['id'])
                else:
                    logger.error("❌ Failed to save video - no result returned")
                    return None
                    
            finally:
                await self.connections.pg_pool.release(conn)
                
        except Exception as e:
            logger.error(f"❌ Failed to save video: {e}")
            return None

    async def save_video(self, video_path: str, url: str, 
                        transcript_data: Optional[List[Dict]] = None,
                        scenes_data: Optional[List[Dict]] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Save video to simple_videos table (legacy method, defaults to carousel_index=0).
        
        Args:
            video_path: Path to video file
            url: Video URL
            transcript_data: Optional transcript segments
            scenes_data: Optional scene descriptions
            metadata: Optional additional metadata
            
        Returns:
            Video ID if successful, None if failed
        """
        return await self.save_video_carousel(video_path, url, 0, transcript_data, scenes_data, metadata)

    async def get_video_by_url_and_index(self, url: str, carousel_index: int) -> Optional[Dict[str, Any]]:
        """
        Get video by URL and carousel index.
        
        Args:
            url: Normalized URL
            carousel_index: Carousel index
            
        Returns:
            Video data if found, None if not found
        """
        if not await self._ensure_connection():
            return None
        
        try:
            conn = await self.connections.pg_pool.acquire()
            try:
                query = """
                SELECT id, url, carousel_index, transcript, descriptions, tags, metadata, created_at, updated_at,
                       CASE WHEN video_base64 IS NOT NULL THEN true ELSE false END as has_video
                FROM simple_videos 
                WHERE url = $1 AND carousel_index = $2;
                """
                
                result = await conn.fetchrow(query, url, carousel_index)
                
                if result:
                    return {
                        "id": str(result["id"]),
                        "url": result["url"],
                        "carousel_index": result["carousel_index"],
                        "transcript": result["transcript"],
                        "descriptions": result["descriptions"],
                        "tags": result["tags"],
                        "metadata": result["metadata"],
                        "has_video": result["has_video"],
                        "created_at": result["created_at"],
                        "updated_at": result["updated_at"]
                    }
                else:
                    return None
                    
            finally:
                await self.connections.pg_pool.release(conn)
                
        except Exception as e:
            logger.error(f"❌ Failed to get video by URL and index: {e}")
            return None

    async def get_videos_by_url(self, url: str, include_base64: bool = False) -> List[Dict[str, Any]]:
        """
        Get all videos for a URL (carousel support).
        
        Args:
            url: Normalized URL
            include_base64: Whether to include base64 video data
            
        Returns:
            List of video data
        """
        if not await self._ensure_connection():
            return []
        
        try:
            conn = await self.connections.pg_pool.acquire()
            try:
                if include_base64:
                    query = """
                    SELECT id, url, carousel_index, video_base64, transcript, descriptions, tags, metadata, 
                           created_at, updated_at,
                           CASE WHEN video_base64 IS NOT NULL THEN true ELSE false END as has_video,
                           length(video_base64) as video_size
                    FROM simple_videos 
                    WHERE url = $1
                    ORDER BY carousel_index;
                    """
                else:
                    query = """
                    SELECT id, url, carousel_index, transcript, descriptions, tags, metadata, 
                           created_at, updated_at,
                           CASE WHEN video_base64 IS NOT NULL THEN true ELSE false END as has_video,
                           length(video_base64) as video_size
                    FROM simple_videos 
                    WHERE url = $1
                    ORDER BY carousel_index;
                    """
                
                results = await conn.fetch(query, url)
                
                videos = []
                for result in results:
                    video_data = {
                        "id": str(result["id"]),
                        "url": result["url"],
                        "carousel_index": result["carousel_index"],
                        "transcript": result["transcript"],
                        "descriptions": result["descriptions"],
                        "tags": result["tags"] or [],
                        "metadata": result["metadata"],
                        "has_video": result["has_video"],
                        "video_size": result["video_size"] or 0,
                        "created_at": result["created_at"].isoformat(),
                        "updated_at": result["updated_at"].isoformat()
                    }
                    
                    if include_base64 and result["video_base64"]:
                        video_data["video_base64"] = result["video_base64"]
                    
                    videos.append(video_data)
                
                return videos
                    
            finally:
                await self.connections.pg_pool.release(conn)
                
        except Exception as e:
            logger.error(f"❌ Failed to get videos by URL: {e}")
            return []

    async def get_video_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get first video by URL (legacy method for backward compatibility).
        
        Args:
            url: Video URL
            
        Returns:
            Video data if found, None if not found
        """
        videos = await self.get_videos_by_url(url)
        return videos[0] if videos else None

    async def get_video(self, video_id: str, include_base64: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get video by ID.
        
        Args:
            video_id: Video UUID
            include_base64: Whether to include base64 video data
            
        Returns:
            Video data if found, None if not found
        """
        if not await self._ensure_connection():
            return None
        
        try:
            conn = await self.connections.pg_pool.acquire()
            try:
                if include_base64:
                    query = """
                    SELECT id, url, carousel_index, video_base64, transcript, descriptions, tags, metadata, 
                           created_at, updated_at,
                           CASE WHEN video_base64 IS NOT NULL THEN true ELSE false END as has_video,
                           length(video_base64) as video_size
                    FROM simple_videos 
                    WHERE id = $1;
                    """
                else:
                    query = """
                    SELECT id, url, carousel_index, transcript, descriptions, tags, metadata, 
                           created_at, updated_at,
                           CASE WHEN video_base64 IS NOT NULL THEN true ELSE false END as has_video,
                           length(video_base64) as video_size
                    FROM simple_videos 
                    WHERE id = $1;
                    """
                
                result = await conn.fetchrow(query, video_id)
                
                if result:
                    video_data = {
                        "id": str(result["id"]),
                        "url": result["url"],
                        "carousel_index": result["carousel_index"],
                        "transcript": result["transcript"],
                        "descriptions": result["descriptions"],
                        "tags": result["tags"] or [],
                        "metadata": result["metadata"],
                        "has_video": result["has_video"],
                        "video_size": result["video_size"] or 0,
                        "created_at": result["created_at"].isoformat(),
                        "updated_at": result["updated_at"].isoformat()
                    }
                    
                    if include_base64 and result["video_base64"]:
                        video_data["video_base64"] = result["video_base64"]
                    
                    return video_data
                else:
                    return None
                    
            finally:
                await self.connections.pg_pool.release(conn)
                
        except Exception as e:
            logger.error(f"❌ Failed to get video: {e}")
            return None

    async def get_video_base64(self, video_id: str) -> Optional[str]:
        """
        Get video base64 data by ID.
        
        Args:
            video_id: Video UUID
            
        Returns:
            Base64 video data if found, None if not found
        """
        if not await self._ensure_connection():
            return None
        
        try:
            conn = await self.connections.pg_pool.acquire()
            try:
                query = "SELECT video_base64 FROM simple_videos WHERE id = $1;"
                result = await conn.fetchrow(query, video_id)
                
                if result and result["video_base64"]:
                    return result["video_base64"]
                else:
                    return None
                    
            finally:
                await self.connections.pg_pool.release(conn)
                
        except Exception as e:
            logger.error(f"❌ Failed to get video base64: {e}")
            return None

    async def update_vectorization_status(self, video_id: str, vector_info: str, embedding_model: str = "text-embedding-3-small") -> bool:
        """
        Update PostgreSQL with vectorization status after successful Qdrant storage.
        
        Args:
            video_id: Video UUID
            vector_info: Vector information (e.g., "5_vectors" for count or single vector ID for backward compatibility)
            embedding_model: OpenAI model used for embeddings
            
        Returns:
            True if successful, False if failed
        """
        if not await self._ensure_connection():
            logger.error("❌ Database connection not available")
            return False
        
        try:
            conn = await self.connections.pg_pool.acquire()
            try:
                update_query = """
                UPDATE simple_videos 
                SET vectorized_at = NOW(), 
                    vector_id = $1, 
                    embedding_model = $2
                WHERE id = $3;
                """
                
                result = await conn.execute(update_query, vector_info, embedding_model, video_id)
                
                if result == "UPDATE 1":
                    logger.debug(f"✅ Updated vectorization status for video: {video_id} ({vector_info})")
                    return True
                else:
                    logger.warning(f"⚠️ No rows updated for video: {video_id}")
                    return False
                    
            finally:
                await self.connections.pg_pool.release(conn)
                
        except Exception as e:
            logger.error(f"❌ Failed to update vectorization status: {e}")
            return False

    async def update_video(self, video_id: str, 
                          video_path: Optional[str] = None,
                          transcript_data: Optional[List[Dict]] = None,
                          scenes_data: Optional[List[Dict]] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Update existing video with new data.
        
        Args:
            video_id: Video UUID to update
            video_path: Optional new video file path
            transcript_data: Optional new transcript data
            scenes_data: Optional new scene descriptions
            metadata: Optional new metadata
            
        Returns:
            Video ID if successful, None if failed
        """
        if not await self._ensure_connection():
            return None
        
        try:
            # Prepare update data
            updates = []
            params = []
            param_count = 0
            
            # Video base64 update
            if video_path:
                with open(video_path, 'rb') as f:
                    video_content = f.read()
                    video_base64 = base64.b64encode(video_content).decode('utf-8')
                param_count += 1
                updates.append(f"video_base64 = ${param_count}")
                params.append(video_base64)
            
            # Transcript update
            if transcript_data is not None:
                param_count += 1
                updates.append(f"transcript = ${param_count}")
                params.append(transcript_data)
            
            # Scenes/descriptions update
            if scenes_data is not None:
                # Extract descriptions and tags from scenes
                descriptions = []
                all_tags = set()
                
                for scene in scenes_data:
                    description_obj = {
                        "start_time": scene.get("start_time"),
                        "end_time": scene.get("end_time"),
                        "description": scene.get("ai_description", ""),
                        "analysis_success": scene.get("analysis_success", False)
                    }
                    
                    # Include transcript context if available
                    if scene.get("has_transcript"):
                        description_obj["has_transcript"] = True
                        description_obj["scene_transcript"] = scene.get("scene_transcript")
                    
                    descriptions.append(description_obj)
                    
                    # Collect tags
                    scene_tags = scene.get("ai_tags", [])
                    all_tags.update(scene_tags)
                
                param_count += 1
                updates.append(f"descriptions = ${param_count}")
                params.append(descriptions)
                
                param_count += 1
                updates.append(f"tags = ${param_count}")
                params.append(list(all_tags))
            
            # Metadata update
            if metadata is not None:
                param_count += 1
                updates.append(f"metadata = ${param_count}")
                params.append(json.dumps(metadata))  # Convert to JSON string
            
            if not updates:
                logger.warning("No updates provided")
                return video_id
            
            # Add video_id as final parameter
            param_count += 1
            params.append(video_id)
            
            # Build and execute update query
            update_query = f"""
            UPDATE simple_videos 
            SET {', '.join(updates)}, updated_at = NOW()
            WHERE id = ${param_count}
            RETURNING id;
            """
            
            conn = await self.connections.pg_pool.acquire()
            try:
                result = await conn.fetchrow(update_query, *params)
                
                if result:
                    logger.info(f"✅ Video updated: {video_id}")
                    return str(result['id'])
                else:
                    logger.error(f"❌ Failed to update video: {video_id}")
                    return None
                    
            finally:
                await self.connections.pg_pool.release(conn)
                
        except Exception as e:
            logger.error(f"❌ Failed to update video: {e}")
            return None

    async def search_videos(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search videos by content using Qdrant vector search."""
        if not await self._ensure_connection():
            return []
        
        try:
            # Try vector search first if Qdrant is available
            if self.connections and self.connections.qdrant_client and self.connections.openai_client:
                return await self._search_videos_vector(query, limit)
            else:
                # Fallback to PostgreSQL text search
                return await self._search_videos_text(query, limit)
                
        except Exception as e:
            logger.error(f"❌ Failed to search videos: {e}")
            # Fallback to text search if vector search fails
            return await self._search_videos_text(query, limit)
    
    async def _search_videos_vector(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search videos using Qdrant vector search."""
        try:
            # Generate embedding for search query
            embedding = await self.connections.generate_embedding(query)
            if not embedding:
                logger.warning("Failed to generate embedding, falling back to text search")
                return await self._search_videos_text(query, limit)
            
            # Search both collections
            collections = ["video_transcript_segments", "video_scene_descriptions"]
            all_results = []
            
            for collection_name in collections:
                try:
                    results = self.connections.qdrant_client.search(
                        collection_name=collection_name,
                        query_vector=embedding,
                        limit=limit,
                        score_threshold=0.3,  # Minimum relevance score
                        with_payload=True
                    )
                    
                    for result in results:
                        payload = result.payload
                        video_id = payload.get("video_id")
                        
                        # Skip if no video_id
                        if not video_id:
                            continue
                        
                        all_results.append({
                            "video_id": video_id,
                            "score": float(result.score),
                            "collection": collection_name,
                            "text": payload.get("text", payload.get("description", "")),
                            "type": payload.get("type", "unknown"),
                            "url": payload.get("url", ""),
                            "carousel_index": payload.get("carousel_index", 0),
                            "created_at": payload.get("created_at", "")
                        })
                        
                except Exception as e:
                    logger.warning(f"Search failed for collection {collection_name}: {e}")
                    continue
            
            # Remove duplicates and sort by score
            unique_videos = {}
            for result in all_results:
                video_id = result["video_id"]
                if video_id not in unique_videos or result["score"] > unique_videos[video_id]["score"]:
                    unique_videos[video_id] = result
            
            # Sort by relevance score (highest first)
            sorted_results = sorted(unique_videos.values(), key=lambda x: x["score"], reverse=True)
            
            # Limit results
            limited_results = sorted_results[:limit]
            
            # Get full video metadata from PostgreSQL for the matched videos
            final_results = []
            for result in limited_results:
                video_id = result["video_id"]
                
                # Get full video data from PostgreSQL
                video_data = await self.get_video(video_id, include_base64=False)
                
                if video_data:
                    # Add search relevance info
                    video_data.update({
                        "search_score": result["score"],
                        "matched_text": result["text"][:200],
                        "match_type": result["type"],
                        "collection": result["collection"]
                    })
                    final_results.append(video_data)
            
            logger.info(f"✅ Vector search found {len(final_results)} videos for query: '{query}'")
            return final_results
            
        except Exception as e:
            logger.error(f"❌ Vector search failed: {e}")
            return await self._search_videos_text(query, limit)
    
    async def _search_videos_text(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fallback PostgreSQL text search."""
        try:
            conn = await self.connections.pg_pool.acquire()
            try:
                search_query = """
                SELECT id, url, carousel_index, tags, metadata, created_at,
                       descriptions -> 0 ->> 'description' as first_description
                FROM simple_videos 
                WHERE 
                    descriptions::text ILIKE $1 
                    OR array_to_string(tags, ' ') ILIKE $1
                    OR metadata::text ILIKE $1
                    OR url ILIKE $1
                ORDER BY created_at DESC
                LIMIT $2;
                """
                
                search_term = f"%{query}%"
                results = await conn.fetch(search_query, search_term, limit)
                
                return [
                    {
                        "id": str(row["id"]),
                        "url": row["url"],
                        "carousel_index": row["carousel_index"],
                        "tags": row["tags"] or [],
                        "first_description": row["first_description"],
                        "created_at": row["created_at"].isoformat(),
                        "search_method": "text"
                    }
                    for row in results
                ]
            finally:
                await self.connections.pg_pool.release(conn)
                
        except Exception as e:
            logger.error(f"❌ Text search failed: {e}")
            return []
    
    async def list_recent_videos(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get most recent videos."""
        if not await self._ensure_connection():
            return []
        
        try:
            conn = await self.connections.pg_pool.acquire()
            try:
                query = """
                SELECT id, url, carousel_index, tags, created_at,
                       descriptions -> 0 ->> 'description' as first_description,
                       CASE WHEN video_base64 IS NOT NULL THEN true ELSE false END as has_video
                FROM simple_videos 
                ORDER BY created_at DESC
                LIMIT $1;
                """
                
                results = await conn.fetch(query, limit)
                
                return [
                    {
                        "id": str(row["id"]),
                        "url": row["url"],
                        "carousel_index": row["carousel_index"],
                        "tags": row["tags"] or [],
                        "first_description": row["first_description"],
                        "has_video": row["has_video"],
                        "created_at": row["created_at"].isoformat()
                    }
                    for row in results
                ]
            finally:
                await self.connections.pg_pool.release(conn)
                
        except Exception as e:
            logger.error(f"❌ Failed to list videos: {e}")
            return []

# Global instance
simple_db = SimpleVideoDatabase()

async def get_simple_db() -> SimpleVideoDatabase:
    """Get the global simple database instance."""
    if not simple_db.connections:
        await simple_db.initialize()
    return simple_db 