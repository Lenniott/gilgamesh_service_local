#!/usr/bin/env python3
"""
Generated Video Database Operations for Video Compilation Pipeline
Handles CRUD operations for the generated_videos table with full metadata support
"""

import logging
import json
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from app.db_connections import DatabaseConnections
from app.ai_script_generator import CompilationScript

logger = logging.getLogger(__name__)

class GeneratedVideoDatabase:
    """
    Database operations for generated videos.
    Follows the same patterns as SimpleVideoDatabase for consistency.
    """
    
    def __init__(self, connections: DatabaseConnections):
        self.connections = connections
    
    async def _ensure_connection(self) -> bool:
        """Ensure database connection is available."""
        if not self.connections or not self.connections.pg_pool:
            logger.error("❌ Database connection not available")
            return False
        return True
    
    async def save_generated_video(self, 
                                 video_base64: str,
                                 script: CompilationScript,
                                 title: str,
                                 user_context: str,
                                 user_requirements: str,
                                 audio_segments: Optional[List[Dict[str, Any]]] = None,
                                 voice_model: str = "alloy",
                                 resolution: str = "720p",
                                 processing_time: Optional[float] = None,
                                 description: Optional[str] = None) -> Optional[str]:
        """
        Save generated video with full metadata.
        
        Args:
            video_base64: Final composed video as base64 string
            script: CompilationScript with all segments and assignments
            title: User-provided or auto-generated title
            user_context: Original user context
            user_requirements: Original user requirements
            audio_segments: Generated audio metadata and base64 data
            voice_model: OpenAI TTS voice model used
            resolution: Output resolution
            processing_time: Total processing time in seconds
            description: Optional description
            
        Returns:
            Generated video ID if successful, None if failed
        """
        if not await self._ensure_connection():
            return None
        
        try:
            # Calculate video metadata
            file_size = len(video_base64.encode('utf-8')) if video_base64 else 0
            duration = script.total_duration
            source_video_ids = [segment.assigned_video_id for segment in script.segments]
            source_videos_count = len(set(source_video_ids))  # Unique count
            
            # Prepare script as JSONB
            script_dict = {
                "total_duration": script.total_duration,
                "segments": [
                    {
                        "script_text": segment.script_text,
                        "start_time": segment.start_time,
                        "end_time": segment.end_time,
                        "assigned_video_id": segment.assigned_video_id,
                        "assigned_video_start": segment.assigned_video_start,
                        "assigned_video_end": segment.assigned_video_end,
                        "transition_type": segment.transition_type,
                        "segment_type": segment.segment_type
                    }
                    for segment in script.segments
                ],
                "metadata": script.metadata
            }
            
            # Generate tags from script content
            tags = self._extract_tags_from_script(script)
            
            # Prepare generation metadata
            generation_metadata = {
                "script_generation": script.metadata,
                "processing_details": {
                    "processing_time": processing_time,
                    "voice_model": voice_model,
                    "resolution": resolution,
                    "file_size": file_size,
                    "generation_timestamp": datetime.now().isoformat()
                },
                "source_analysis": {
                    "unique_videos_used": source_videos_count,
                    "total_segments": len(script.segments),
                    "segment_types": self._count_segment_types(script.segments)
                }
            }
            
            # Get fresh connection and insert
            conn = await self.connections.pg_pool.acquire()
            try:
                video_id = str(uuid.uuid4())
                
                insert_query = """
                INSERT INTO generated_videos (
                    id, title, description, user_requirements, compilation_script, 
                    source_video_ids, audio_segments, video_base64, duration, 
                    resolution, file_size, generation_metadata, tags, voice_model, 
                    processing_time, source_videos_count
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                RETURNING id;
                """
                
                result = await conn.fetchrow(
                    insert_query,
                    video_id,
                    title,
                    description,
                    f"{user_context} | {user_requirements}",  # Combined requirements
                    json.dumps(script_dict),  # JSONB
                    source_video_ids,  # TEXT[]
                    json.dumps(audio_segments) if audio_segments else None,  # JSONB
                    video_base64,
                    duration,
                    resolution,
                    file_size,
                    json.dumps(generation_metadata),  # JSONB
                    tags,  # TEXT[]
                    voice_model,
                    processing_time,
                    source_videos_count
                )
                
                if result:
                    logger.info(f"✅ Generated video saved to database: {video_id} "
                               f"(duration: {duration:.1f}s, videos used: {source_videos_count})")
                    return str(result['id'])
                else:
                    logger.error("❌ Failed to save generated video - no result returned")
                    return None
                    
            finally:
                await self.connections.pg_pool.release(conn)
                
        except Exception as e:
            logger.error(f"❌ Failed to save generated video: {e}")
            return None
    
    async def get_generated_video(self, video_id: str, include_base64: bool = False) -> Optional[Dict[str, Any]]:
        """
        Retrieve generated video by ID.
        
        Args:
            video_id: Generated video UUID
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
                    SELECT id, title, description, user_requirements, compilation_script, 
                           source_video_ids, audio_segments, video_base64, duration, 
                           resolution, file_size, generation_metadata, tags, voice_model, 
                           processing_time, source_videos_count, created_at, updated_at
                    FROM generated_videos 
                    WHERE id = $1;
                    """
                else:
                    query = """
                    SELECT id, title, description, user_requirements, compilation_script, 
                           source_video_ids, audio_segments, duration, 
                           resolution, file_size, generation_metadata, tags, voice_model, 
                           processing_time, source_videos_count, created_at, updated_at,
                           CASE WHEN video_base64 IS NOT NULL THEN true ELSE false END as has_video
                    FROM generated_videos 
                    WHERE id = $1;
                    """
                
                result = await conn.fetchrow(query, video_id)
                
                if result:
                    video_data = {
                        "id": str(result["id"]),
                        "title": result["title"],
                        "description": result["description"],
                        "user_requirements": result["user_requirements"],
                        "compilation_script": result["compilation_script"],
                        "source_video_ids": result["source_video_ids"],
                        "audio_segments": result["audio_segments"],
                        "duration": result["duration"],
                        "resolution": result["resolution"],
                        "file_size": result["file_size"],
                        "generation_metadata": result["generation_metadata"],
                        "tags": result["tags"] or [],
                        "voice_model": result["voice_model"],
                        "processing_time": result["processing_time"],
                        "source_videos_count": result["source_videos_count"],
                        "created_at": result["created_at"].isoformat(),
                        "updated_at": result["updated_at"].isoformat()
                    }
                    
                    if include_base64 and result.get("video_base64"):
                        video_data["video_base64"] = result["video_base64"]
                    elif not include_base64:
                        video_data["has_video"] = result.get("has_video", False)
                    
                    return video_data
                else:
                    return None
                    
            finally:
                await self.connections.pg_pool.release(conn)
                
        except Exception as e:
            logger.error(f"❌ Failed to get generated video: {e}")
            return None
    
    async def search_generated_videos(self, 
                                    query: str, 
                                    duration_min: Optional[float] = None,
                                    duration_max: Optional[float] = None,
                                    resolution: Optional[str] = None,
                                    voice_model: Optional[str] = None,
                                    tags: Optional[List[str]] = None,
                                    limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search generated videos by content and metadata.
        
        Args:
            query: Search query for title and requirements
            duration_min: Minimum duration filter
            duration_max: Maximum duration filter
            resolution: Resolution filter
            voice_model: Voice model filter
            tags: Tags filter (any of these tags)
            limit: Maximum results to return
            
        Returns:
            List of matching video data
        """
        if not await self._ensure_connection():
            return []
        
        try:
            conn = await self.connections.pg_pool.acquire()
            try:
                # Build dynamic WHERE clause
                where_conditions = []
                params = []
                param_count = 0
                
                # Text search
                if query:
                    param_count += 1
                    where_conditions.append(f"""
                        (title ILIKE ${param_count} 
                         OR user_requirements ILIKE ${param_count}
                         OR array_to_string(tags, ' ') ILIKE ${param_count})
                    """)
                    params.append(f"%{query}%")
                
                # Duration filters
                if duration_min is not None:
                    param_count += 1
                    where_conditions.append(f"duration >= ${param_count}")
                    params.append(duration_min)
                
                if duration_max is not None:
                    param_count += 1
                    where_conditions.append(f"duration <= ${param_count}")
                    params.append(duration_max)
                
                # Resolution filter
                if resolution:
                    param_count += 1
                    where_conditions.append(f"resolution = ${param_count}")
                    params.append(resolution)
                
                # Voice model filter
                if voice_model:
                    param_count += 1
                    where_conditions.append(f"voice_model = ${param_count}")
                    params.append(voice_model)
                
                # Tags filter (any of the specified tags)
                if tags:
                    param_count += 1
                    where_conditions.append(f"tags && ${param_count}")
                    params.append(tags)
                
                # Build final query
                where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                
                param_count += 1
                params.append(limit)
                
                search_query = f"""
                SELECT id, title, description, duration, resolution, voice_model, 
                       tags, source_videos_count, processing_time, created_at,
                       CASE WHEN video_base64 IS NOT NULL THEN true ELSE false END as has_video
                FROM generated_videos 
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_count};
                """
                
                results = await conn.fetch(search_query, *params)
                
                return [
                    {
                        "id": str(row["id"]),
                        "title": row["title"],
                        "description": row["description"],
                        "duration": row["duration"],
                        "resolution": row["resolution"],
                        "voice_model": row["voice_model"],
                        "tags": row["tags"] or [],
                        "source_videos_count": row["source_videos_count"],
                        "processing_time": row["processing_time"],
                        "has_video": row["has_video"],
                        "created_at": row["created_at"].isoformat()
                    }
                    for row in results
                ]
            finally:
                await self.connections.pg_pool.release(conn)
                
        except Exception as e:
            logger.error(f"❌ Failed to search generated videos: {e}")
            return []
    
    async def list_recent_generated_videos(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        List recently generated videos.
        
        Args:
            limit: Maximum results to return
            
        Returns:
            List of recent video data
        """
        if not await self._ensure_connection():
            return []
        
        try:
            conn = await self.connections.pg_pool.acquire()
            try:
                query = """
                SELECT id, title, description, duration, resolution, voice_model, 
                       tags, source_videos_count, processing_time, created_at,
                       CASE WHEN video_base64 IS NOT NULL THEN true ELSE false END as has_video
                FROM generated_videos 
                ORDER BY created_at DESC
                LIMIT $1;
                """
                
                results = await conn.fetch(query, limit)
                
                return [
                    {
                        "id": str(row["id"]),
                        "title": row["title"],
                        "description": row["description"],
                        "duration": row["duration"],
                        "resolution": row["resolution"],
                        "voice_model": row["voice_model"],
                        "tags": row["tags"] or [],
                        "source_videos_count": row["source_videos_count"],
                        "processing_time": row["processing_time"],
                        "has_video": row["has_video"],
                        "created_at": row["created_at"].isoformat()
                    }
                    for row in results
                ]
            finally:
                await self.connections.pg_pool.release(conn)
                
        except Exception as e:
            logger.error(f"❌ Failed to list recent generated videos: {e}")
            return []
    
    async def get_generated_video_base64(self, video_id: str) -> Optional[str]:
        """
        Get generated video base64 data by ID.
        
        Args:
            video_id: Generated video UUID
            
        Returns:
            Base64 video data if found, None if not found
        """
        if not await self._ensure_connection():
            return None
        
        try:
            conn = await self.connections.pg_pool.acquire()
            try:
                query = "SELECT video_base64 FROM generated_videos WHERE id = $1;"
                result = await conn.fetchrow(query, video_id)
                
                if result and result["video_base64"]:
                    return result["video_base64"]
                else:
                    return None
                    
            finally:
                await self.connections.pg_pool.release(conn)
                
        except Exception as e:
            logger.error(f"❌ Failed to get generated video base64: {e}")
            return None
    
    async def update_generated_video(self, 
                                   video_id: str,
                                   title: Optional[str] = None,
                                   description: Optional[str] = None,
                                   tags: Optional[List[str]] = None) -> bool:
        """
        Update generated video metadata.
        
        Args:
            video_id: Generated video UUID
            title: New title
            description: New description
            tags: New tags
            
        Returns:
            True if successful, False if failed
        """
        if not await self._ensure_connection():
            return False
        
        try:
            # Build dynamic update query
            updates = []
            params = []
            param_count = 0
            
            if title is not None:
                param_count += 1
                updates.append(f"title = ${param_count}")
                params.append(title)
            
            if description is not None:
                param_count += 1
                updates.append(f"description = ${param_count}")
                params.append(description)
            
            if tags is not None:
                param_count += 1
                updates.append(f"tags = ${param_count}")
                params.append(tags)
            
            if not updates:
                logger.warning("No updates provided")
                return True
            
            # Add video_id as final parameter
            param_count += 1
            params.append(video_id)
            
            # Build and execute update query
            update_query = f"""
            UPDATE generated_videos 
            SET {', '.join(updates)}, updated_at = NOW()
            WHERE id = ${param_count}
            RETURNING id;
            """
            
            conn = await self.connections.pg_pool.acquire()
            try:
                result = await conn.fetchrow(update_query, *params)
                
                if result:
                    logger.info(f"✅ Generated video updated: {video_id}")
                    return True
                else:
                    logger.error(f"❌ Failed to update generated video: {video_id}")
                    return False
                    
            finally:
                await self.connections.pg_pool.release(conn)
                
        except Exception as e:
            logger.error(f"❌ Failed to update generated video: {e}")
            return False
    
    async def delete_generated_video(self, video_id: str) -> bool:
        """
        Delete generated video by ID.
        
        Args:
            video_id: Generated video UUID
            
        Returns:
            True if successful, False if failed
        """
        if not await self._ensure_connection():
            return False
        
        try:
            conn = await self.connections.pg_pool.acquire()
            try:
                delete_query = "DELETE FROM generated_videos WHERE id = $1 RETURNING id;"
                result = await conn.fetchrow(delete_query, video_id)
                
                if result:
                    logger.info(f"✅ Generated video deleted: {video_id}")
                    return True
                else:
                    logger.warning(f"⚠️ Generated video not found for deletion: {video_id}")
                    return False
                    
            finally:
                await self.connections.pg_pool.release(conn)
                
        except Exception as e:
            logger.error(f"❌ Failed to delete generated video: {e}")
            return False
    
    async def get_generation_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about generated videos.
        
        Returns:
            Dictionary with generation statistics
        """
        if not await self._ensure_connection():
            return {}
        
        try:
            conn = await self.connections.pg_pool.acquire()
            try:
                stats_query = """
                SELECT 
                    COUNT(*) as total_videos,
                    AVG(duration) as avg_duration,
                    AVG(processing_time) as avg_processing_time,
                    AVG(source_videos_count) as avg_source_videos,
                    SUM(file_size) as total_file_size,
                    MIN(created_at) as first_generation,
                    MAX(created_at) as latest_generation
                FROM generated_videos
                WHERE processing_time IS NOT NULL;
                """
                
                result = await conn.fetchrow(stats_query)
                
                # Get resolution distribution
                resolution_query = """
                SELECT resolution, COUNT(*) as count
                FROM generated_videos
                GROUP BY resolution
                ORDER BY count DESC;
                """
                resolution_results = await conn.fetch(resolution_query)
                
                # Get voice model distribution
                voice_query = """
                SELECT voice_model, COUNT(*) as count
                FROM generated_videos
                GROUP BY voice_model
                ORDER BY count DESC;
                """
                voice_results = await conn.fetch(voice_query)
                
                return {
                    "total_videos": result["total_videos"] or 0,
                    "average_duration": float(result["avg_duration"] or 0),
                    "average_processing_time": float(result["avg_processing_time"] or 0),
                    "average_source_videos": float(result["avg_source_videos"] or 0),
                    "total_file_size": result["total_file_size"] or 0,
                    "first_generation": result["first_generation"].isoformat() if result["first_generation"] else None,
                    "latest_generation": result["latest_generation"].isoformat() if result["latest_generation"] else None,
                    "resolution_distribution": {row["resolution"]: row["count"] for row in resolution_results},
                    "voice_model_distribution": {row["voice_model"]: row["count"] for row in voice_results}
                }
                
            finally:
                await self.connections.pg_pool.release(conn)
                
        except Exception as e:
            logger.error(f"❌ Failed to get generation statistics: {e}")
            return {}
    
    def _extract_tags_from_script(self, script: CompilationScript) -> List[str]:
        """Extract relevant tags from script content."""
        tags = set()
        
        # Add tags based on segment types
        for segment in script.segments:
            tags.add(segment.segment_type)
            
            # Extract keywords from script text
            script_text_lower = segment.script_text.lower()
            
            # Common fitness keywords
            fitness_keywords = [
                "workout", "exercise", "strength", "cardio", "flexibility", 
                "mobility", "core", "abs", "legs", "arms", "back", "chest",
                "beginner", "intermediate", "advanced", "warm", "cool",
                "stretch", "movement", "training", "fitness"
            ]
            
            for keyword in fitness_keywords:
                if keyword in script_text_lower:
                    tags.add(keyword)
        
        # Limit to most relevant tags
        return list(tags)[:10]
    
    def _count_segment_types(self, segments) -> Dict[str, int]:
        """Count segment types for metadata."""
        segment_types = {}
        for segment in segments:
            segment_type = segment.segment_type
            segment_types[segment_type] = segment_types.get(segment_type, 0) + 1
        return segment_types

# Global instance factory
async def get_generated_video_db(connections: DatabaseConnections) -> GeneratedVideoDatabase:
    """Get a GeneratedVideoDatabase instance."""
    return GeneratedVideoDatabase(connections) 