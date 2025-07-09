#!/usr/bin/env python3
"""
Migration Tools for Base64 to File-Based Storage
Handles one-time migration of existing base64 data to file-based storage.
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import base64
import tempfile

from app.clip_storage import get_clip_storage
from app.clip_operations import extract_clip_from_video, validate_clip_file
from app.simple_db_operations import SimpleVideoDatabase

logger = logging.getLogger(__name__)

class MigrationManager:
    """
    Manages the migration from base64 to file-based storage.
    """
    
    def __init__(self):
        self.clip_storage = get_clip_storage()
        self.db = None
        self.migration_stats = {
            "total_videos": 0,
            "processed_videos": 0,
            "failed_videos": 0,
            "total_clips": 0,
            "successful_clips": 0,
            "failed_clips": 0,
            "total_size_bytes": 0,
            "start_time": None,
            "end_time": None
        }
    
    async def initialize(self):
        """Initialize database connection."""
        self.db = SimpleVideoDatabase()
        await self.db.initialize()
        logger.info("✅ Migration manager initialized")
    
    async def get_videos_for_migration(self) -> List[Dict]:
        """
        Get all videos that need migration (have base64 data but no file metadata).
        
        Returns:
            List of video records that need migration
        """
        if not self.db or not self.db.connections or not self.db.connections.pg_pool:
            raise ValueError("Database not initialized")
        
        try:
            conn = await self.db.connections.pg_pool.acquire()
            try:
                # Get videos with base64 data but no file metadata
                query = """
                    SELECT id, url, carousel_index, video_base64, descriptions, transcript, metadata
                    FROM simple_videos 
                    WHERE video_base64 IS NOT NULL 
                    AND (video_metadata IS NULL OR video_metadata = '{}'::jsonb)
                    ORDER BY created_at DESC
                """
                
                result = await conn.fetch(query)
                videos = []
                
                for row in result:
                    videos.append({
                        "id": row["id"],
                        "url": row["url"],
                        "carousel_index": row["carousel_index"],
                        "video_base64": row["video_base64"],
                        "descriptions": row["descriptions"],
                        "transcript": row["transcript"],
                        "metadata": row["metadata"]
                    })
                
                logger.info(f"📋 Found {len(videos)} videos for migration")
                return videos
                
            finally:
                await self.db.connections.pg_pool.release(conn)
                
        except Exception as e:
            logger.error(f"❌ Failed to get videos for migration: {e}")
            return []
    
    async def migrate_video(self, video_data: Dict) -> Dict:
        """
        Migrate a single video from base64 to file-based storage.
        
        Args:
            video_data: Video data with base64 content
            
        Returns:
            Migration result for this video
        """
        video_id = video_data["id"]
        video_base64 = video_data["video_base64"]
        descriptions = video_data["descriptions"]
        
        result = {
            "video_id": video_id,
            "success": False,
            "clips_created": 0,
            "clips_failed": 0,
            "error": None,
            "clip_paths": []
        }
        
        try:
            logger.info(f"🔄 Migrating video: {video_id}")
            
            # Decode base64 to temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                temp_path = temp_file.name
                video_bytes = base64.b64decode(video_base64)
                temp_file.write(video_bytes)
            
            try:
                # Parse descriptions if it's a JSON string
                if descriptions and isinstance(descriptions, str):
                    try:
                        descriptions = json.loads(descriptions)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse descriptions JSON for video {video_id}: {e}")
                        descriptions = []
                
                # Process each scene description
                if descriptions and isinstance(descriptions, list):
                    for scene_index, scene in enumerate(descriptions):
                        scene_result = await self._migrate_scene(
                            video_id, scene, scene_index, temp_path
                        )
                        
                        if scene_result["success"]:
                            result["clips_created"] += 1
                            result["clip_paths"].append(scene_result["clip_path"])
                        else:
                            result["clips_failed"] += 1
                            logger.warning(f"⚠️ Failed to migrate scene {scene_index}: {scene_result['error']}")
                
                # Update video metadata
                if result["clips_created"] > 0:
                    await self._update_video_metadata(video_id, descriptions, result["clip_paths"])
                    result["success"] = True
                    logger.info(f"✅ Successfully migrated video {video_id}: {result['clips_created']} clips")
                else:
                    result["error"] = "No clips were successfully created"
                    logger.error(f"❌ Failed to migrate video {video_id}: no clips created")
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"❌ Failed to migrate video {video_id}: {e}")
        
        return result
    
    async def _migrate_scene(self, video_id: str, scene: Dict, scene_index: int, 
                            source_video_path: str) -> Dict:
        """
        Migrate a single scene from base64 to file.
        
        Args:
            video_id: Video UUID
            scene: Scene description data
            scene_index: Index of the scene
            source_video_path: Path to the source video file
            
        Returns:
            Migration result for this scene
        """
        result = {
            "success": False,
            "clip_path": None,
            "error": None
        }
        
        try:
            # Generate scene ID if not present
            scene_id = scene.get("scene_id", f"scene_{scene_index}")
            
            # Get scene timing
            start_time = scene.get("start_time", 0)
            end_time = scene.get("end_time", 0)
            
            if start_time >= end_time:
                result["error"] = f"Invalid scene timing: {start_time} >= {end_time}"
                return result
            
            # Save clip to file storage
            clip_result = self.clip_storage.save_clip(
                video_id, scene_id, scene_index, source_video_path, start_time, end_time
            )
            
            result["clip_path"] = clip_result["clip_path"]
            result["success"] = True
            
            logger.debug(f"✅ Migrated scene {scene_index}: {clip_result['clip_path']}")
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"❌ Failed to migrate scene {scene_index}: {e}")
        
        return result
    
    async def _update_video_metadata(self, video_id: str, descriptions: List[Dict], 
                                   clip_paths: List[str]) -> bool:
        """
        Update video metadata with file-based information.
        
        Args:
            video_id: Video UUID
            descriptions: Scene descriptions
            clip_paths: List of clip file paths
            
        Returns:
            True if update was successful
        """
        try:
            # Create new video metadata structure
            video_metadata = {
                "scenes": [],
                "transcript": [],  # Will be populated if transcript exists
                "rawTranscript": "",
                "migration_info": {
                    "migrated_at": datetime.now().isoformat(),
                    "clip_count": len(clip_paths),
                    "storage_version": 2
                }
            }
            
            # Update scene descriptions with file paths
            for i, scene in enumerate(descriptions):
                scene_id = scene.get("scene_id", f"scene_{i}")
                clip_path = clip_paths[i] if i < len(clip_paths) else None
                
                updated_scene = {
                    "scene_id": scene_id,
                    "description": scene.get("description", ""),
                    "clip_path": clip_path,
                    "tags": scene.get("ai_tags", []),
                    "start": scene.get("start_time", 0),
                    "end": scene.get("end_time", 0)
                }
                
                video_metadata["scenes"].append(updated_scene)
            
            # Update database
            if self.db and self.db.connections and self.db.connections.pg_pool:
                conn = await self.db.connections.pg_pool.acquire()
                try:
                    query = """
                        UPDATE simple_videos 
                        SET video_metadata = $1, clip_storage_version = 2
                        WHERE id = $2
                    """
                    await conn.execute(query, json.dumps(video_metadata), video_id)
                    
                    logger.info(f"✅ Updated video metadata for {video_id}")
                    return True
                    
                finally:
                    await self.db.connections.pg_pool.release(conn)
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to update video metadata for {video_id}: {e}")
            return False
    
    async def run_migration(self, dry_run: bool = False) -> Dict:
        """
        Run the complete migration process.
        
        Args:
            dry_run: If True, only simulate the migration without making changes
            
        Returns:
            Migration statistics and results
        """
        self.migration_stats["start_time"] = datetime.now()
        logger.info(f"🚀 Starting migration (dry_run={dry_run})")
        
        try:
            # Get videos for migration
            videos = await self.get_videos_for_migration()
            self.migration_stats["total_videos"] = len(videos)
            
            if not videos:
                logger.info("✅ No videos found for migration")
                return self.migration_stats
            
            # Process each video
            for video_data in videos:
                if dry_run:
                    logger.info(f"🔍 DRY RUN: Would migrate video {video_data['id']}")
                    self.migration_stats["processed_videos"] += 1
                    continue
                
                result = await self.migrate_video(video_data)
                
                if result["success"]:
                    self.migration_stats["processed_videos"] += 1
                    self.migration_stats["successful_clips"] += result["clips_created"]
                else:
                    self.migration_stats["failed_videos"] += 1
                    self.migration_stats["failed_clips"] += result["clips_failed"]
                
                self.migration_stats["total_clips"] += result["clips_created"] + result["clips_failed"]
            
            self.migration_stats["end_time"] = datetime.now()
            
            # Log final statistics
            logger.info("📊 Migration completed:")
            logger.info(f"   Videos processed: {self.migration_stats['processed_videos']}/{self.migration_stats['total_videos']}")
            logger.info(f"   Videos failed: {self.migration_stats['failed_videos']}")
            logger.info(f"   Clips created: {self.migration_stats['successful_clips']}")
            logger.info(f"   Clips failed: {self.migration_stats['failed_clips']}")
            
            return self.migration_stats
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            self.migration_stats["end_time"] = datetime.now()
            self.migration_stats["error"] = str(e)
            return self.migration_stats
    
    async def validate_migration(self) -> Dict:
        """
        Validate the migration by checking file integrity and database consistency.
        
        Returns:
            Validation results
        """
        logger.info("🔍 Validating migration...")
        
        validation_results = {
            "total_videos_checked": 0,
            "videos_with_files": 0,
            "videos_without_files": 0,
            "invalid_files": 0,
            "orphaned_files": 0,
            "errors": []
        }
        
        try:
            # Get all videos with file metadata
            if self.db and self.db.connections and self.db.connections.pg_pool:
                conn = await self.db.connections.pg_pool.acquire()
                try:
                    query = """
                        SELECT id, video_metadata, descriptions
                        FROM simple_videos 
                        WHERE video_metadata IS NOT NULL 
                        AND video_metadata != '{}'::jsonb
                    """
                    
                    result = await conn.fetch(query)
                    
                    for row in result:
                        video_id = row["id"]
                        video_metadata = row["video_metadata"]
                        descriptions = row["descriptions"]
                        
                        validation_results["total_videos_checked"] += 1
                        
                        if video_metadata and isinstance(video_metadata, dict):
                            scenes = video_metadata.get("scenes", [])
                            
                            if scenes:
                                validation_results["videos_with_files"] += 1
                                
                                # Check each scene file
                                for scene in scenes:
                                    clip_path = scene.get("clip_path")
                                    if clip_path:
                                        if not self.clip_storage.validate_clip_file(clip_path):
                                            validation_results["invalid_files"] += 1
                                            validation_results["errors"].append(
                                                f"Invalid file for video {video_id}: {clip_path}"
                                            )
                            else:
                                validation_results["videos_without_files"] += 1
                                validation_results["errors"].append(
                                    f"Video {video_id} has metadata but no scene files"
                                )
                
                finally:
                    await self.db.connections.pg_pool.release(conn)
            
            # Check for orphaned files
            storage_stats = self.clip_storage.get_storage_stats()
            if "total_files" in storage_stats:
                validation_results["orphaned_files"] = storage_stats["total_files"]
            
            logger.info("✅ Validation completed:")
            logger.info(f"   Videos checked: {validation_results['total_videos_checked']}")
            logger.info(f"   Videos with files: {validation_results['videos_with_files']}")
            logger.info(f"   Videos without files: {validation_results['videos_without_files']}")
            logger.info(f"   Invalid files: {validation_results['invalid_files']}")
            logger.info(f"   Orphaned files: {validation_results['orphaned_files']}")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"❌ Validation failed: {e}")
            validation_results["errors"].append(f"Validation error: {e}")
            return validation_results
    
    async def rollback_migration(self, video_ids: List[str] = None) -> Dict:
        """
        Rollback migration for specific videos or all migrated videos.
        
        Args:
            video_ids: List of video IDs to rollback, or None for all
            
        Returns:
            Rollback results
        """
        logger.info("🔄 Starting migration rollback...")
        
        rollback_results = {
            "videos_rolled_back": 0,
            "files_deleted": 0,
            "errors": []
        }
        
        try:
            # Get videos to rollback
            if video_ids is None:
                # Get all migrated videos
                if self.db and self.db.connections and self.db.connections.pg_pool:
                    conn = await self.db.connections.pg_pool.acquire()
                    try:
                        query = """
                            SELECT id FROM simple_videos 
                            WHERE clip_storage_version = 2
                        """
                        result = await conn.fetch(query)
                        video_ids = [row["id"] for row in result]
                    finally:
                        await self.db.connections.pg_pool.release(conn)
            
            # Rollback each video
            for video_id in video_ids:
                try:
                    # Delete clip files
                    deleted_count = self.clip_storage.delete_video_clips(video_id)
                    
                    # Reset database record
                    if self.db and self.db.connections and self.db.connections.pg_pool:
                        conn = await self.db.connections.pg_pool.acquire()
                        try:
                            query = """
                                UPDATE simple_videos 
                                SET video_metadata = NULL, clip_storage_version = 1
                                WHERE id = $1
                            """
                            await conn.execute(query, video_id)
                        finally:
                            await self.db.connections.pg_pool.release(conn)
                    
                    rollback_results["videos_rolled_back"] += 1
                    rollback_results["files_deleted"] += deleted_count
                    
                    logger.info(f"✅ Rolled back video {video_id}: {deleted_count} files deleted")
                    
                except Exception as e:
                    error_msg = f"Failed to rollback video {video_id}: {e}"
                    rollback_results["errors"].append(error_msg)
                    logger.error(f"❌ {error_msg}")
            
            logger.info(f"🔄 Rollback completed: {rollback_results['videos_rolled_back']} videos, {rollback_results['files_deleted']} files")
            return rollback_results
            
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            rollback_results["errors"].append(f"Rollback error: {e}")
            return rollback_results


# Convenience functions for easy migration

async def migrate_base64_to_files(dry_run: bool = False) -> Dict:
    """
    One-time migration function to convert existing base64 data to files.
    
    Args:
        dry_run: If True, only simulate the migration
        
    Returns:
        Migration results
    """
    migration_manager = MigrationManager()
    await migration_manager.initialize()
    return await migration_manager.run_migration(dry_run)

async def validate_migration() -> Dict:
    """
    Validate the migration by checking file integrity and database consistency.
    
    Returns:
        Validation results
    """
    migration_manager = MigrationManager()
    await migration_manager.initialize()
    return await migration_manager.validate_migration()

async def rollback_migration(video_ids: List[str] = None) -> Dict:
    """
    Rollback migration for specific videos or all migrated videos.
    
    Args:
        video_ids: List of video IDs to rollback, or None for all
        
    Returns:
        Rollback results
    """
    migration_manager = MigrationManager()
    await migration_manager.initialize()
    return await migration_manager.rollback_migration(video_ids) 