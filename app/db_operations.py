import os
import uuid
import json
import base64
import asyncio
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
import logging

from app.db_connections import get_db_connections, DatabaseConnections

logger = logging.getLogger(__name__)

class GilgameshDatabaseOperations:
    """Database operations for Gilgamesh video processing with flexible storage options."""
    
    def __init__(self):
        self.connections: Optional[DatabaseConnections] = None
    
    async def initialize(self) -> Dict[str, bool]:
        """Initialize database connections."""
        self.connections = await get_db_connections()
        return await self.connections.test_all_connections()
    
    # --- VIDEO SAVING FUNCTIONALITY ---
    
    async def save_video_to_database(self, video_path: str, url: str, 
                                   metadata: Dict[str, Any], 
                                   save_to_postgres: bool = True) -> Optional[str]:
        """
        Save video as base64 in PostgreSQL.
        
        Args:
            video_path: Path to the video file
            url: Original URL of the video
            metadata: Video metadata (title, description, etc.)
            save_to_postgres: Whether to save to PostgreSQL
            
        Returns:
            str: Video ID if successful, None if failed
        """
        if not save_to_postgres or not self.connections.pg_pool:
            logger.warning("PostgreSQL saving disabled or unavailable")
            return None
        
        try:
            # Read video file and encode as base64
            with open(video_path, 'rb') as video_file:
                video_bytes = video_file.read()
                video_base64 = base64.b64encode(video_bytes).decode('utf-8')
            
            async with self.connections.get_pg_connection_context() as conn:
                async with conn.transaction():
                    # 1. Insert or get post
                    post_id = await self._insert_or_get_post(conn, url, metadata)
                    
                    # 2. Insert video with base64 data
                    video_query = """
                    INSERT INTO gilgamesh_sm_videos (
                        id, post_id, transcript, created_at
                    ) VALUES (
                        gen_random_uuid(), $1::uuid, $2, CURRENT_TIMESTAMP
                    )
                    RETURNING id;
                    """
                    
                    video_id = await conn.fetchval(
                        video_query,
                        post_id,
                        json.dumps({"video_base64": video_base64, "original_url": url})
                    )
                    
                    logger.info(f"✅ Saved video to PostgreSQL: {video_id}")
                    return str(video_id)
                    
        except Exception as e:
            logger.error(f"❌ Failed to save video to database: {e}")
            return None
    
    # --- TRANSCRIPTION FUNCTIONALITY ---
    
    async def save_transcription(self, transcript_data: List[Dict], video_id: str, url: str,
                               save_to_postgres: bool = True, 
                               save_to_qdrant: bool = True,
                               chunk_by_timestamp: bool = True) -> Dict[str, Any]:
        """
        Save transcription with chunking and vectorization.
        
        Args:
            transcript_data: List of transcript segments with start/end times
            video_id: Video ID for linking
            url: Original URL for metadata
            save_to_postgres: Whether to save to PostgreSQL
            save_to_qdrant: Whether to save to Qdrant
            chunk_by_timestamp: Whether to chunk by timestamps
            
        Returns:
            Dict with results and metadata
        """
        results = {
            "postgresql_saved": False,
            "qdrant_saved": False,
            "chunks_created": 0,
            "vector_ids": []
        }
        
        try:
            # Process transcript chunks
            if chunk_by_timestamp and transcript_data:
                chunks = self._create_transcript_chunks(transcript_data)
            else:
                # Single chunk with full transcript
                full_text = " ".join([seg.get('text', '') for seg in transcript_data])
                chunks = [{
                    "text": full_text,
                    "start_time": transcript_data[0].get('start', 0.0) if transcript_data else 0.0,
                    "end_time": transcript_data[-1].get('end', 0.0) if transcript_data else 0.0,
                    "chunk_index": 0
                }]
            
            results["chunks_created"] = len(chunks)
            
            # Save to PostgreSQL
            if save_to_postgres and self.connections.pg_pool:
                pg_success = await self._save_transcript_to_postgres(chunks, video_id, url)
                results["postgresql_saved"] = pg_success
            
            # Save to Qdrant
            if save_to_qdrant and self.connections.qdrant_client:
                vector_ids = await self._save_transcript_to_qdrant(chunks, video_id, url)
                results["qdrant_saved"] = len(vector_ids) > 0
                results["vector_ids"] = vector_ids
            
            logger.info(f"✅ Transcript saved: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to save transcription: {e}")
            return results
    
    def _create_transcript_chunks(self, transcript_data: List[Dict], 
                                chunk_duration: float = 30.0) -> List[Dict]:
        """Create transcript chunks based on time duration."""
        chunks = []
        current_chunk = {"text": "", "start_time": None, "end_time": None, "segments": []}
        
        for segment in transcript_data:
            start = segment.get('start', 0.0)
            end = segment.get('end', 0.0)
            text = segment.get('text', '')
            
            # Start new chunk if needed
            if current_chunk["start_time"] is None:
                current_chunk["start_time"] = start
            
            # Check if we should start a new chunk
            if (current_chunk["start_time"] and 
                start - current_chunk["start_time"] > chunk_duration):
                
                # Finalize current chunk
                if current_chunk["segments"]:
                    current_chunk["end_time"] = current_chunk["segments"][-1].get('end', 0.0)
                    current_chunk["chunk_index"] = len(chunks)
                    chunks.append(current_chunk.copy())
                
                # Start new chunk
                current_chunk = {
                    "text": text,
                    "start_time": start,
                    "end_time": end,
                    "segments": [segment]
                }
            else:
                # Add to current chunk
                current_chunk["text"] += " " + text if current_chunk["text"] else text
                current_chunk["end_time"] = end
                current_chunk["segments"].append(segment)
        
        # Add final chunk
        if current_chunk["segments"]:
            current_chunk["chunk_index"] = len(chunks)
            chunks.append(current_chunk)
        
        return chunks
    
    async def _save_transcript_to_postgres(self, chunks: List[Dict], 
                                         video_id: str, url: str) -> bool:
        """Save transcript chunks to PostgreSQL."""
        try:
            async with self.connections.get_pg_connection_context() as conn:
                async with conn.transaction():
                    for chunk in chunks:
                        # Insert into video scenes table with transcript
                        scene_query = """
                        INSERT INTO gilgamesh_sm_video_scenes (
                            id, video_id, start_time, end_time, transcript, 
                            onscreen_text, base64_snippet, created_at
                        ) VALUES (
                            gen_random_uuid(), $1::uuid, $2, $3, $4, $5, NULL, CURRENT_TIMESTAMP
                        );
                        """
                        
                        await conn.execute(
                            scene_query,
                            video_id,
                            chunk["start_time"],
                            chunk["end_time"],
                            chunk["text"],
                            json.dumps({  # Store metadata in onscreen_text
                                "chunk_index": chunk["chunk_index"],
                                "segment_count": len(chunk.get("segments", [])),
                                "original_url": url,
                                "type": "transcript_chunk"
                            })
                        )
            
            logger.info(f"✅ Saved {len(chunks)} transcript chunks to PostgreSQL")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save transcript to PostgreSQL: {e}")
            return False
    
    async def _save_transcript_to_qdrant(self, chunks: List[Dict], 
                                       video_id: str, url: str) -> List[str]:
        """Save transcript chunks to Qdrant with embeddings."""
        vector_ids = []
        
        try:
            # Ensure collection exists
            await self.connections.ensure_collection_exists("gilgamesh_transcripts")
            
            # Process each chunk
            for chunk in chunks:
                # Generate embedding
                embedding = await self.connections.generate_embedding(chunk["text"])
                if not embedding:
                    continue
                
                # Create vector ID
                vector_id = str(uuid.uuid4())
                
                # Create metadata for retrieval
                metadata = {
                    "video_id": video_id,
                    "original_url": url,
                    "start_time": chunk["start_time"],
                    "end_time": chunk["end_time"],
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                    "type": "transcript",
                    "created_at": datetime.utcnow().isoformat(),
                    "segment_count": len(chunk.get("segments", []))
                }
                
                # Store vector
                success = await self.connections.store_vector(
                    "gilgamesh_transcripts", vector_id, embedding, metadata
                )
                
                if success:
                    vector_ids.append(vector_id)
                    
                    # Update PostgreSQL with vector_id if available
                    if self.connections.pg_pool:
                        await self._update_scene_vector_id(video_id, chunk, vector_id)
            
            logger.info(f"✅ Saved {len(vector_ids)} transcript vectors to Qdrant")
            return vector_ids
            
        except Exception as e:
            logger.error(f"❌ Failed to save transcript to Qdrant: {e}")
            return vector_ids
    
    # --- SCENE DESCRIPTION FUNCTIONALITY ---
    
    async def save_scene_descriptions(self, scenes_data: List[Dict], video_id: str, url: str,
                                    save_to_postgres: bool = True,
                                    save_to_qdrant: bool = True) -> Dict[str, Any]:
        """
        Save scene descriptions and AI analysis.
        
        Args:
            scenes_data: List of scene data with AI descriptions
            video_id: Video ID for linking
            url: Original URL
            save_to_postgres: Whether to save to PostgreSQL
            save_to_qdrant: Whether to save to Qdrant
            
        Returns:
            Dict with results and metadata
        """
        results = {
            "postgresql_saved": False,
            "qdrant_saved": False,
            "scenes_processed": 0,
            "vector_ids": []
        }
        
        try:
            # Save to PostgreSQL
            if save_to_postgres and self.connections.pg_pool:
                pg_success = await self._save_scenes_to_postgres(scenes_data, video_id, url)
                results["postgresql_saved"] = pg_success
            
            # Save to Qdrant
            if save_to_qdrant and self.connections.qdrant_client:
                vector_ids = await self._save_scenes_to_qdrant(scenes_data, video_id, url)
                results["qdrant_saved"] = len(vector_ids) > 0
                results["vector_ids"] = vector_ids
            
            results["scenes_processed"] = len(scenes_data)
            logger.info(f"✅ Scene descriptions saved: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to save scene descriptions: {e}")
            return results
    
    async def _save_scenes_to_postgres(self, scenes_data: List[Dict], 
                                     video_id: str, url: str) -> bool:
        """Save scene data to PostgreSQL."""
        try:
            async with self.connections.get_pg_connection_context() as conn:
                async with conn.transaction():
                    for scene in scenes_data:
                        # Insert scene
                        scene_query = """
                        INSERT INTO gilgamesh_sm_video_scenes (
                            id, video_id, start_time, end_time, transcript, 
                            onscreen_text, base64_snippet, created_at
                        ) VALUES (
                            gen_random_uuid(), $1::uuid, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP
                        )
                        RETURNING id;
                        """
                        
                        scene_id = await conn.fetchval(
                            scene_query,
                            video_id,
                            scene.get("start_time", 0.0),
                            scene.get("end_time", 0.0),
                            scene.get("ai_description", ""),
                            json.dumps({
                                "type": "scene_description",
                                "analysis_success": scene.get("analysis_success", False),
                                "original_url": url
                            }),
                            scene.get("video")  # base64 video snippet
                        )
                        
                        # Insert AI metadata
                        if scene.get("ai_tags") or scene.get("ai_description"):
                            metadata_query = """
                            INSERT INTO gilgamesh_sm_scene_exercise_metadata (
                                id, scene_id, tags, how_to, created_at
                            ) VALUES (
                                gen_random_uuid(), $1::uuid, $2, $3, CURRENT_TIMESTAMP
                            );
                            """
                            
                            await conn.execute(
                                metadata_query,
                                scene_id,
                                scene.get("ai_tags", []),
                                scene.get("ai_description", "")
                            )
            
            logger.info(f"✅ Saved {len(scenes_data)} scenes to PostgreSQL")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save scenes to PostgreSQL: {e}")
            return False
    
    async def _save_scenes_to_qdrant(self, scenes_data: List[Dict], 
                                   video_id: str, url: str) -> List[str]:
        """Save scene descriptions to Qdrant with embeddings."""
        vector_ids = []
        
        try:
            # Ensure collection exists
            await self.connections.ensure_collection_exists("gilgamesh_scenes")
            
            # Process each scene
            for i, scene in enumerate(scenes_data):
                description = scene.get("ai_description", "")
                if not description:
                    continue
                
                # Generate embedding
                embedding = await self.connections.generate_embedding(description)
                if not embedding:
                    continue
                
                # Create vector ID
                vector_id = str(uuid.uuid4())
                
                # Create metadata for retrieval
                metadata = {
                    "video_id": video_id,
                    "original_url": url,
                    "start_time": scene.get("start_time", 0.0),
                    "end_time": scene.get("end_time", 0.0),
                    "scene_index": i,
                    "description": description,
                    "tags": scene.get("ai_tags", []),
                    "analysis_success": scene.get("analysis_success", False),
                    "type": "scene_description",
                    "created_at": datetime.utcnow().isoformat()
                }
                
                # Store vector
                success = await self.connections.store_vector(
                    "gilgamesh_scenes", vector_id, embedding, metadata
                )
                
                if success:
                    vector_ids.append(vector_id)
            
            logger.info(f"✅ Saved {len(vector_ids)} scene vectors to Qdrant")
            return vector_ids
            
        except Exception as e:
            logger.error(f"❌ Failed to save scenes to Qdrant: {e}")
            return vector_ids
    
    # --- HELPER METHODS ---
    
    async def _insert_or_get_post(self, conn, url: str, metadata: Dict[str, Any]) -> str:
        """Insert or get existing post."""
        # Extract platform from URL
        platform = self._extract_platform(url)
        
        # Insert or update post
        post_query = """
        INSERT INTO gilgamesh_sm_posts (
            id, post_url, generated_description, source_platform, 
            original_description, created_at, updated_at
        ) VALUES (
            gen_random_uuid(), $1, $2, $3, $4, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
        ON CONFLICT (post_url) DO UPDATE SET
            generated_description = EXCLUDED.generated_description,
            original_description = EXCLUDED.original_description,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id;
        """
        
        post_id = await conn.fetchval(
            post_query,
            url,
            metadata.get("title", ""),
            platform,
            metadata.get("description", "")
        )
        
        return str(post_id)
    
    def _extract_platform(self, url: str) -> str:
        """Extract platform name from URL."""
        url_lower = url.lower()
        if 'instagram.com' in url_lower:
            return 'instagram'
        elif any(domain in url_lower for domain in ['youtube.com', 'youtu.be']):
            return 'youtube'
        elif 'tiktok.com' in url_lower:
            return 'tiktok'
        else:
            return 'unknown'
    
    async def _update_scene_vector_id(self, video_id: str, chunk: Dict, vector_id: str):
        """Update scene record with vector ID."""
        try:
            async with self.connections.get_pg_connection_context() as conn:
                update_query = """
                UPDATE gilgamesh_sm_video_scenes 
                SET vector_id = $1::uuid
                WHERE video_id = $2::uuid 
                AND start_time = $3 
                AND end_time = $4;
                """
                
                await conn.execute(
                    update_query,
                    vector_id,
                    video_id,
                    chunk["start_time"],
                    chunk["end_time"]
                )
        except Exception as e:
            logger.warning(f"Could not update vector_id: {e}")
    
    # --- RETRIEVAL METHODS ---
    
    async def get_full_video_from_chunk(self, vector_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve full video information from a single chunk's vector ID.
        
        Args:
            vector_id: Vector ID from Qdrant search result
            
        Returns:
            Dict with full video information and metadata
        """
        try:
            # Search Qdrant for the specific vector
            if not self.connections.qdrant_client:
                return None
            
            # Get the point from Qdrant
            points = self.connections.qdrant_client.retrieve(
                collection_name="gilgamesh_transcripts",
                ids=[vector_id]
            )
            
            if not points:
                # Try scenes collection
                points = self.connections.qdrant_client.retrieve(
                    collection_name="gilgamesh_scenes",
                    ids=[vector_id]
                )
            
            if not points:
                return None
            
            point = points[0]
            metadata = point.payload
            video_id = metadata.get("video_id")
            
            if not video_id:
                return None
            
            # Get full video information from PostgreSQL
            async with self.connections.get_pg_connection_context() as conn:
                video_query = """
                SELECT v.*, p.post_url, p.original_description, p.source_platform
                FROM gilgamesh_sm_videos v
                JOIN gilgamesh_sm_posts p ON v.post_id = p.id
                WHERE v.id = $1::uuid;
                """
                
                video_record = await conn.fetchrow(video_query, video_id)
                
                if not video_record:
                    return None
                
                # Get all scenes for this video
                scenes_query = """
                SELECT * FROM gilgamesh_sm_video_scenes 
                WHERE video_id = $1::uuid 
                ORDER BY start_time;
                """
                
                scenes = await conn.fetch(scenes_query, video_id)
                
                return {
                    "video_id": str(video_record["id"]),
                    "original_url": video_record["post_url"],
                    "description": video_record["original_description"],
                    "platform": video_record["source_platform"],
                    "full_transcript": video_record["transcript"],
                    "scenes": [dict(scene) for scene in scenes],
                    "matched_chunk": {
                        "vector_id": vector_id,
                        "text": metadata.get("text"),
                        "start_time": metadata.get("start_time"),
                        "end_time": metadata.get("end_time"),
                        "type": metadata.get("type")
                    }
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to retrieve full video from chunk: {e}")
            return None

    # --- TRANSCRIPTION FUNCTIONALITY ---
    
    async def save_transcription(self, transcript_data: List[Dict], video_id: str, url: str,
                               save_to_postgres: bool = True, 
                               save_to_qdrant: bool = True,
                               chunk_by_timestamp: bool = True) -> Dict[str, Any]:
        """Save transcription with chunking and vectorization."""
        results = {
            "postgresql_saved": False,
            "qdrant_saved": False,
            "chunks_created": 0,
            "vector_ids": []
        }
        
        try:
            # Process transcript chunks
            if chunk_by_timestamp and transcript_data:
                chunks = self._create_transcript_chunks(transcript_data)
            else:
                # Single chunk with full transcript
                full_text = " ".join([seg.get('text', '') for seg in transcript_data])
                chunks = [{
                    "text": full_text,
                    "start_time": transcript_data[0].get('start', 0.0) if transcript_data else 0.0,
                    "end_time": transcript_data[-1].get('end', 0.0) if transcript_data else 0.0,
                    "chunk_index": 0
                }]
            
            results["chunks_created"] = len(chunks)
            
            # Save to PostgreSQL
            if save_to_postgres and self.connections.pg_pool:
                pg_success = await self._save_transcript_to_postgres(chunks, video_id, url)
                results["postgresql_saved"] = pg_success
            
            # Save to Qdrant
            if save_to_qdrant and self.connections.qdrant_client:
                vector_ids = await self._save_transcript_to_qdrant(chunks, video_id, url)
                results["qdrant_saved"] = len(vector_ids) > 0
                results["vector_ids"] = vector_ids
            
            logger.info(f"✅ Transcript saved: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to save transcription: {e}")
            return results
    
    def _create_transcript_chunks(self, transcript_data: List[Dict], 
                                chunk_duration: float = 30.0) -> List[Dict]:
        """Create transcript chunks based on time duration."""
        chunks = []
        current_chunk = {"text": "", "start_time": None, "end_time": None, "segments": []}
        
        for segment in transcript_data:
            start = segment.get('start', 0.0)
            end = segment.get('end', 0.0)
            text = segment.get('text', '')
            
            # Start new chunk if needed
            if current_chunk["start_time"] is None:
                current_chunk["start_time"] = start
            
            # Check if we should start a new chunk
            if (current_chunk["start_time"] and 
                start - current_chunk["start_time"] > chunk_duration):
                
                # Finalize current chunk
                if current_chunk["segments"]:
                    current_chunk["end_time"] = current_chunk["segments"][-1].get('end', 0.0)
                    current_chunk["chunk_index"] = len(chunks)
                    chunks.append(current_chunk.copy())
                
                # Start new chunk
                current_chunk = {
                    "text": text,
                    "start_time": start,
                    "end_time": end,
                    "segments": [segment]
                }
            else:
                # Add to current chunk
                current_chunk["text"] += " " + text if current_chunk["text"] else text
                current_chunk["end_time"] = end
                current_chunk["segments"].append(segment)
        
        # Add final chunk
        if current_chunk["segments"]:
            current_chunk["chunk_index"] = len(chunks)
            chunks.append(current_chunk)
        
        return chunks
    
    async def _save_transcript_to_postgres(self, chunks: List[Dict], 
                                         video_id: str, url: str) -> bool:
        """Save transcript chunks to PostgreSQL."""
        try:
            async with self.connections.get_pg_connection_context() as conn:
                async with conn.transaction():
                    for chunk in chunks:
                        # Insert into video scenes table with transcript
                        scene_query = """
                        INSERT INTO gilgamesh_sm_video_scenes (
                            id, video_id, start_time, end_time, transcript, 
                            onscreen_text, base64_snippet, created_at
                        ) VALUES (
                            gen_random_uuid(), $1::uuid, $2, $3, $4, $5, NULL, CURRENT_TIMESTAMP
                        );
                        """
                        
                        await conn.execute(
                            scene_query,
                            video_id,
                            chunk["start_time"],
                            chunk["end_time"],
                            chunk["text"],
                            json.dumps({  # Store metadata in onscreen_text
                                "chunk_index": chunk["chunk_index"],
                                "segment_count": len(chunk.get("segments", [])),
                                "original_url": url,
                                "type": "transcript_chunk"
                            })
                        )
            
            logger.info(f"✅ Saved {len(chunks)} transcript chunks to PostgreSQL")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save transcript to PostgreSQL: {e}")
            return False
    
    async def _save_transcript_to_qdrant(self, chunks: List[Dict], 
                                       video_id: str, url: str) -> List[str]:
        """Save transcript chunks to Qdrant with embeddings."""
        vector_ids = []
        
        try:
            # Ensure collection exists
            await self.connections.ensure_collection_exists("gilgamesh_transcripts")
            
            # Process each chunk
            for chunk in chunks:
                # Generate embedding
                embedding = await self.connections.generate_embedding(chunk["text"])
                if not embedding:
                    continue
                
                # Create vector ID
                vector_id = str(uuid.uuid4())
                
                # Create metadata for retrieval
                metadata = {
                    "video_id": video_id,
                    "original_url": url,
                    "start_time": chunk["start_time"],
                    "end_time": chunk["end_time"],
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                    "type": "transcript",
                    "created_at": datetime.utcnow().isoformat(),
                    "segment_count": len(chunk.get("segments", []))
                }
                
                # Store vector
                success = await self.connections.store_vector(
                    "gilgamesh_transcripts", vector_id, embedding, metadata
                )
                
                if success:
                    vector_ids.append(vector_id)
            
            logger.info(f"✅ Saved {len(vector_ids)} transcript vectors to Qdrant")
            return vector_ids
            
        except Exception as e:
            logger.error(f"❌ Failed to save transcript to Qdrant: {e}")
            return vector_ids
    
    # --- SCENE DESCRIPTION FUNCTIONALITY ---
    
    async def save_scene_descriptions(self, scenes_data: List[Dict], video_id: str, url: str,
                                    save_to_postgres: bool = True,
                                    save_to_qdrant: bool = True) -> Dict[str, Any]:
        """Save scene descriptions and AI analysis."""
        results = {
            "postgresql_saved": False,
            "qdrant_saved": False,
            "scenes_processed": 0,
            "vector_ids": []
        }
        
        try:
            # Save to PostgreSQL
            if save_to_postgres and self.connections.pg_pool:
                pg_success = await self._save_scenes_to_postgres(scenes_data, video_id, url)
                results["postgresql_saved"] = pg_success
            
            # Save to Qdrant
            if save_to_qdrant and self.connections.qdrant_client:
                vector_ids = await self._save_scenes_to_qdrant(scenes_data, video_id, url)
                results["qdrant_saved"] = len(vector_ids) > 0
                results["vector_ids"] = vector_ids
            
            results["scenes_processed"] = len(scenes_data)
            logger.info(f"✅ Scene descriptions saved: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to save scene descriptions: {e}")
            return results
    
    async def _save_scenes_to_postgres(self, scenes_data: List[Dict], 
                                     video_id: str, url: str) -> bool:
        """Save scene data to PostgreSQL."""
        try:
            async with self.connections.get_pg_connection_context() as conn:
                async with conn.transaction():
                    for scene in scenes_data:
                        # Insert scene
                        scene_query = """
                        INSERT INTO gilgamesh_sm_video_scenes (
                            id, video_id, start_time, end_time, transcript, 
                            onscreen_text, base64_snippet, created_at
                        ) VALUES (
                            gen_random_uuid(), $1::uuid, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP
                        )
                        RETURNING id;
                        """
                        
                        scene_id = await conn.fetchval(
                            scene_query,
                            video_id,
                            scene.get("start_time", 0.0),
                            scene.get("end_time", 0.0),
                            scene.get("ai_description", ""),
                            json.dumps({
                                "type": "scene_description",
                                "analysis_success": scene.get("analysis_success", False),
                                "original_url": url
                            }),
                            scene.get("video")  # base64 video snippet
                        )
                        
                        # Insert AI metadata
                        if scene.get("ai_tags") or scene.get("ai_description"):
                            metadata_query = """
                            INSERT INTO gilgamesh_sm_scene_exercise_metadata (
                                id, scene_id, tags, how_to, created_at
                            ) VALUES (
                                gen_random_uuid(), $1::uuid, $2, $3, CURRENT_TIMESTAMP
                            );
                            """
                            
                            await conn.execute(
                                metadata_query,
                                scene_id,
                                scene.get("ai_tags", []),
                                scene.get("ai_description", "")
                            )
            
            logger.info(f"✅ Saved {len(scenes_data)} scenes to PostgreSQL")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save scenes to PostgreSQL: {e}")
            return False
    
    async def _save_scenes_to_qdrant(self, scenes_data: List[Dict], 
                                   video_id: str, url: str) -> List[str]:
        """Save scene descriptions to Qdrant with embeddings."""
        vector_ids = []
        
        try:
            # Ensure collection exists
            await self.connections.ensure_collection_exists("gilgamesh_scenes")
            
            # Process each scene
            for i, scene in enumerate(scenes_data):
                description = scene.get("ai_description", "")
                if not description:
                    continue
                
                # Generate embedding
                embedding = await self.connections.generate_embedding(description)
                if not embedding:
                    continue
                
                # Create vector ID
                vector_id = str(uuid.uuid4())
                
                # Create metadata for retrieval
                metadata = {
                    "video_id": video_id,
                    "original_url": url,
                    "start_time": scene.get("start_time", 0.0),
                    "end_time": scene.get("end_time", 0.0),
                    "scene_index": i,
                    "description": description,
                    "tags": scene.get("ai_tags", []),
                    "analysis_success": scene.get("analysis_success", False),
                    "type": "scene_description",
                    "created_at": datetime.utcnow().isoformat()
                }
                
                # Store vector
                success = await self.connections.store_vector(
                    "gilgamesh_scenes", vector_id, embedding, metadata
                )
                
                if success:
                    vector_ids.append(vector_id)
            
            logger.info(f"✅ Saved {len(vector_ids)} scene vectors to Qdrant")
            return vector_ids
            
        except Exception as e:
            logger.error(f"❌ Failed to save scenes to Qdrant: {e}")
            return vector_ids
    
    # --- HELPER METHODS ---
    
    async def _insert_or_get_post(self, conn, url: str, metadata: Dict[str, Any]) -> str:
        """Insert or get existing post."""
        # Extract platform from URL
        platform = self._extract_platform(url)
        
        # Insert or update post
        post_query = """
        INSERT INTO gilgamesh_sm_posts (
            id, post_url, generated_description, source_platform, 
            original_description, created_at, updated_at
        ) VALUES (
            gen_random_uuid(), $1, $2, $3, $4, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
        ON CONFLICT (post_url) DO UPDATE SET
            generated_description = EXCLUDED.generated_description,
            original_description = EXCLUDED.original_description,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id;
        """
        
        post_id = await conn.fetchval(
            post_query,
            url,
            metadata.get("title", ""),
            platform,
            metadata.get("description", "")
        )
        
        return str(post_id)
    
    def _extract_platform(self, url: str) -> str:
        """Extract platform name from URL."""
        url_lower = url.lower()
        if 'instagram.com' in url_lower:
            return 'instagram'
        elif any(domain in url_lower for domain in ['youtube.com', 'youtu.be']):
            return 'youtube'
        elif 'tiktok.com' in url_lower:
            return 'tiktok'
        else:
            return 'unknown'

# Global instance
db_ops = GilgameshDatabaseOperations()

async def get_db_operations() -> GilgameshDatabaseOperations:
    """Get the global database operations instance."""
    if not db_ops.connections:
        await db_ops.initialize()
    return db_ops 