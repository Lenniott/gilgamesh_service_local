import asyncio
import asyncpg
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class GilgameshDB:
    """Database client for inserting processed media data into Gilgamesh tables."""
    
    def __init__(self, connection_url: str = None):
        """
        Initialize database connection.
        
        Args:
            connection_url: PostgreSQL connection URL
                          Defaults to DATABASE_URL environment variable
        """
        self.connection_url = connection_url or os.getenv('DATABASE_URL')
        if not self.connection_url:
            raise ValueError("DATABASE_URL environment variable is required")
            
        self.pool = None
    
    async def connect(self):
        """Create database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(self.connection_url)
            logger.info("Database connection pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create database connection pool: {e}")
            raise
    
    async def disconnect(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def insert_processed_media(self, processed_data: Dict, user_id: Optional[str] = None) -> str:
        """
        Insert processed media data into Gilgamesh database tables.
        
        Args:
            processed_data: The JSON response from process_single_url()
            user_id: Optional user ID for linking content to users
            
        Returns:
            str: The UUID of the created post
            
        Raises:
            Exception: If database insertion fails
        """
        if not self.pool:
            await self.connect()
            
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                try:
                    # Extract data from processed result
                    url = processed_data.get('url', '')
                    title = processed_data.get('title', '')
                    description = processed_data.get('description', '')
                    tags = processed_data.get('tags', [])
                    videos = processed_data.get('videos', [])
                    images = processed_data.get('images', [])
                    
                    # Determine platform from URL
                    platform = self._extract_platform(url)
                    
                    # 1. Insert main social media post
                    post_id = await self._insert_post(conn, url, title, description, platform)
                    
                    # 2. Insert and link tags
                    if tags:
                        await self._insert_tags(conn, post_id, tags)
                    
                    # 3. Insert videos and their scenes/transcripts
                    video_count = 0
                    total_scenes = 0
                    total_transcripts = 0
                    
                    for video_data in videos:
                        video_id = await self._insert_video(conn, post_id, video_data)
                        video_count += 1
                        
                        # Insert scenes
                        scenes = video_data.get('scenes', [])
                        for scene in scenes:
                            await self._insert_video_scene(conn, video_id, scene)
                            total_scenes += 1
                        
                        # Insert transcripts
                        transcripts = video_data.get('transcript', [])
                        for transcript in transcripts:
                            await self._insert_transcript(conn, video_id, transcript)
                            total_transcripts += 1
                    
                    # 4. Insert images
                    image_count = 0
                    for image_data in images:
                        await self._insert_image(conn, post_id, image_data)
                        image_count += 1
                    
                    # 5. Update media count
                    await self._insert_media_count(conn, post_id, video_count, image_count, 
                                                 total_scenes, total_transcripts)
                    
                    # 6. Link to user content if user_id provided
                    if user_id:
                        await self._insert_user_content(conn, user_id, post_id)
                    
                    logger.info(f"Successfully inserted processed media data for URL: {url}")
                    return post_id
                    
                except Exception as e:
                    logger.error(f"Failed to insert processed media data: {e}")
                    raise
    
    async def _insert_post(self, conn, url: str, title: str, description: str, platform: str) -> str:
        """Insert main social media post."""
        query = """
        INSERT INTO gilgamesh_sm_posts (
            id, url, title, description, platform, processed_at, created_at
        ) VALUES (
            gen_random_uuid(), $1, $2, $3, $4, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        ) 
        ON CONFLICT (url) DO UPDATE SET
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            processed_at = CURRENT_TIMESTAMP
        RETURNING id;
        """
        result = await conn.fetchval(query, url, title, description, platform)
        return str(result)
    
    async def _insert_tags(self, conn, post_id: str, tags: List[str]):
        """Insert tags and link them to the post."""
        for tag_name in tags:
            # Clean tag name (remove # if present)
            clean_tag = tag_name.strip('#').strip()
            if not clean_tag:
                continue
                
            # Insert tag if not exists
            tag_query = """
            INSERT INTO gilgamesh_sm_tags (id, tag_name, created_at)
            VALUES (gen_random_uuid(), $1, CURRENT_TIMESTAMP)
            ON CONFLICT (tag_name) DO NOTHING
            RETURNING id;
            """
            tag_id = await conn.fetchval(tag_query, clean_tag)
            
            # If tag already existed, get its ID
            if not tag_id:
                tag_id = await conn.fetchval(
                    "SELECT id FROM gilgamesh_sm_tags WHERE tag_name = $1", clean_tag
                )
            
            # Link tag to post
            link_query = """
            INSERT INTO gilgamesh_sm_post_tags (id, post_id, tag_id, created_at)
            VALUES (gen_random_uuid(), $1::uuid, $2::uuid, CURRENT_TIMESTAMP)
            ON CONFLICT (post_id, tag_id) DO NOTHING;
            """
            await conn.execute(link_query, post_id, str(tag_id))
    
    async def _insert_video(self, conn, post_id: str, video_data: Dict) -> str:
        """Insert video record."""
        video_identifier = video_data.get('id', '')
        
        # Try to extract file path if available (from temp_dir context)
        file_path = video_data.get('file_path', '')
        
        # Calculate duration from scenes if available
        duration = self._calculate_duration_from_scenes(video_data.get('scenes', []))
        
        query = """
        INSERT INTO gilgamesh_sm_videos (
            id, post_id, video_identifier, file_path, duration_seconds, created_at
        ) VALUES (
            gen_random_uuid(), $1::uuid, $2, $3, $4, CURRENT_TIMESTAMP
        )
        RETURNING id;
        """
        result = await conn.fetchval(query, post_id, video_identifier, file_path, duration)
        return str(result)
    
    async def _insert_video_scene(self, conn, video_id: str, scene_data: Dict):
        """Insert video scene with OCR text."""
        query = """
        INSERT INTO gilgamesh_sm_video_scenes (
            id, video_id, start_time, end_time, ocr_text, confidence_score, video_base64, created_at
        ) VALUES (
            gen_random_uuid(), $1::uuid, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP
        );
        """
        await conn.execute(
            query,
            video_id,
            scene_data.get('start', 0.0),
            scene_data.get('end', 0.0),
            scene_data.get('text', ''),
            scene_data.get('confidence', 1.0),
            scene_data.get('video')  # base64 encoded video (can be None)
        )
    
    async def _insert_transcript(self, conn, video_id: str, transcript_data: Dict):
        """Insert transcript segment."""
        query = """
        INSERT INTO gilgamesh_sm_scene_exercise_metadata (
            id, video_id, start_time, end_time, transcript_text, exercise_type, created_at
        ) VALUES (
            gen_random_uuid(), $1::uuid, $2, $3, $4, 'transcript', CURRENT_TIMESTAMP
        );
        """
        await conn.execute(
            query,
            video_id,
            transcript_data.get('start', 0.0),
            transcript_data.get('end', 0.0),
            transcript_data.get('text', '')
        )
    
    async def _insert_image(self, conn, post_id: str, image_data: Dict):
        """Insert image with OCR text."""
        query = """
        INSERT INTO gilgamesh_sm_images (
            id, post_id, file_path, ocr_text, created_at
        ) VALUES (
            gen_random_uuid(), $1::uuid, $2, $3, CURRENT_TIMESTAMP
        );
        """
        await conn.execute(
            query,
            post_id,
            image_data.get('file_path', ''),
            image_data.get('text', '')
        )
    
    async def _insert_media_count(self, conn, post_id: str, video_count: int, 
                                 image_count: int, total_scenes: int, total_transcripts: int):
        """Insert or update media count for the post."""
        query = """
        INSERT INTO gilgamesh_sm_media_count (
            id, post_id, video_count, image_count, total_scenes, total_transcript_segments, created_at
        ) VALUES (
            gen_random_uuid(), $1::uuid, $2, $3, $4, $5, CURRENT_TIMESTAMP
        )
        ON CONFLICT (post_id) DO UPDATE SET
            video_count = EXCLUDED.video_count,
            image_count = EXCLUDED.image_count,
            total_scenes = EXCLUDED.total_scenes,
            total_transcript_segments = EXCLUDED.total_transcript_segments;
        """
        await conn.execute(query, post_id, video_count, image_count, total_scenes, total_transcripts)
    
    async def _insert_user_content(self, conn, user_id: str, post_id: str):
        """Link content to user."""
        query = """
        INSERT INTO gilgamesh_content (
            id, user_id, post_id, content_type, status, created_at
        ) VALUES (
            gen_random_uuid(), $1::uuid, $2::uuid, 'social_media_post', 'processed', CURRENT_TIMESTAMP
        );
        """
        await conn.execute(query, user_id, post_id)
    
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
    
    def _calculate_duration_from_scenes(self, scenes: List[Dict]) -> Optional[float]:
        """Calculate total duration from scenes."""
        if not scenes:
            return None
        
        # Find the maximum end time
        max_end = max((scene.get('end', 0.0) for scene in scenes), default=0.0)
        return max_end if max_end > 0 else None


# Global database instance
db = GilgameshDB()


async def save_processed_media_to_db(processed_data: Dict, user_id: Optional[str] = None) -> str:
    """
    Convenience function to save processed media data to database.
    
    Args:
        processed_data: The JSON response from process_single_url()
        user_id: Optional user ID for linking content to users
        
    Returns:
        str: The UUID of the created post
    """
    return await db.insert_processed_media(processed_data, user_id) 