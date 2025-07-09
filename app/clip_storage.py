#!/usr/bin/env python3
"""
Clip Storage Management System
Handles file-based storage for video clips extracted from scenes.
"""

import os
import uuid
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import json

logger = logging.getLogger(__name__)

class ClipStorage:
    """
    Manages file-based storage for video clips.
    
    File organization:
    /storage/
    ├── clips/
    │   ├── 2024/
    │   │   ├── 01/
    │   │   │   ├── video_id_1/
    │   │   │   │   ├── scene_001.mp4
    │   │   │   │   ├── scene_002.mp4
    │   │   │   │   └── metadata.json
    │   │   │   └── video_id_2/
    │   │   │       ├── scene_001.mp4
    │   │   │       └── metadata.json
    │   │   └── 02/
    │   └── 2025/
    └── temp/
        └── processing/
    """
    
    def __init__(self, base_storage_path: str = "./storage", max_file_size_mb: int = 500):
        """
        Initialize clip storage system.
        
        Args:
            base_storage_path: Base directory for clip storage
            max_file_size_mb: Maximum file size in MB before cleanup
        """
        self.base_storage_path = Path(base_storage_path)
        self.clips_path = self.base_storage_path / "clips"
        self.temp_path = self.base_storage_path / "temp" / "processing"
        self.max_file_size_mb = max_file_size_mb * 1024 * 1024  # Convert to bytes
        
        # Create directory structure
        self._ensure_directories()
        
        logger.info(f"📁 Clip storage initialized at: {self.base_storage_path}")
        logger.info(f"📁 Clips directory: {self.clips_path}")
        logger.info(f"📁 Temp directory: {self.temp_path}")
    
    def _ensure_directories(self):
        """Ensure all required directories exist."""
        self.clips_path.mkdir(parents=True, exist_ok=True)
        self.temp_path.mkdir(parents=True, exist_ok=True)
        
        # Create year/month directories for current date
        now = datetime.now()
        year_month_path = self.clips_path / str(now.year) / f"{now.month:02d}"
        year_month_path.mkdir(parents=True, exist_ok=True)
    
    def get_video_clip_directory(self, video_id: str) -> Path:
        """
        Get the directory for storing clips for a specific video.
        
        Args:
            video_id: UUID of the video
            
        Returns:
            Path to the video's clip directory
        """
        now = datetime.now()
        year_month = now.strftime("%Y/%m")
        video_dir = self.clips_path / year_month / str(video_id)
        video_dir.mkdir(parents=True, exist_ok=True)
        return video_dir
    
    def generate_clip_filename(self, scene_id: str, scene_index: int) -> str:
        """
        Generate a filename for a clip.
        
        Args:
            scene_id: UUID of the scene
            scene_index: Index of the scene (for ordering)
            
        Returns:
            Filename for the clip
        """
        return f"scene_{scene_index:03d}_{scene_id[:8]}.mp4"
    
    def save_clip(self, video_id: str, scene_id: str, scene_index: int, 
                  source_file_path: str, start_time: float, end_time: float) -> Dict[str, any]:
        """
        Save a clip file to storage.
        
        Args:
            video_id: UUID of the video
            scene_id: UUID of the scene
            scene_index: Index of the scene
            source_file_path: Path to the source video file
            start_time: Start time in original video (seconds)
            end_time: End time in original video (seconds)
            
        Returns:
            Dict with clip information including file path and metadata
        """
        try:
            # Get video directory
            video_dir = self.get_video_clip_directory(video_id)
            
            # Generate clip filename
            clip_filename = self.generate_clip_filename(scene_id, scene_index)
            clip_path = video_dir / clip_filename
            
            # Extract clip using ffmpeg
            duration = end_time - start_time
            
            import subprocess
            cmd = [
                'ffmpeg', '-y',
                '-i', source_file_path,
                '-ss', str(start_time),
                '-t', str(duration),
                '-c:v', 'libx264',
                '-crf', '24',
                '-preset', 'medium',
                '-movflags', '+faststart',
                '-an',  # No audio for clips
                str(clip_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Get file size
            file_size = clip_path.stat().st_size if clip_path.exists() else 0
            
            # Create metadata
            metadata = {
                "scene_id": scene_id,
                "scene_index": scene_index,
                "start_time": start_time,
                "end_time": end_time,
                "duration": duration,
                "file_size": file_size,
                "created_at": datetime.now().isoformat(),
                "source_video": str(source_file_path)
            }
            
            # Save metadata file
            metadata_path = video_dir / f"scene_{scene_index:03d}_{scene_id[:8]}_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"✅ Saved clip: {clip_path} ({file_size} bytes)")
            
            return {
                "clip_path": str(clip_path),
                "metadata_path": str(metadata_path),
                "file_size": file_size,
                "duration": duration,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to save clip for video {video_id}, scene {scene_id}: {e}")
            raise
    
    def get_clip_path(self, video_id: str, scene_id: str, scene_index: int) -> Optional[str]:
        """
        Get the file path for a specific clip.
        
        Args:
            video_id: UUID of the video
            scene_id: UUID of the scene
            scene_index: Index of the scene
            
        Returns:
            Path to the clip file if it exists, None otherwise
        """
        try:
            video_dir = self.get_video_clip_directory(video_id)
            clip_filename = self.generate_clip_filename(scene_id, scene_index)
            clip_path = video_dir / clip_filename
            
            if clip_path.exists():
                return str(clip_path)
            else:
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to get clip path for video {video_id}, scene {scene_id}: {e}")
            return None
    
    def delete_clip(self, video_id: str, scene_id: str, scene_index: int) -> bool:
        """
        Delete a clip file and its metadata.
        
        Args:
            video_id: UUID of the video
            scene_id: UUID of the scene
            scene_index: Index of the scene
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            video_dir = self.get_video_clip_directory(video_id)
            clip_filename = self.generate_clip_filename(scene_id, scene_index)
            clip_path = video_dir / clip_filename
            metadata_path = video_dir / f"scene_{scene_index:03d}_{scene_id[:8]}_metadata.json"
            
            deleted_files = []
            
            # Delete clip file
            if clip_path.exists():
                clip_path.unlink()
                deleted_files.append(str(clip_path))
                logger.info(f"🗑️ Deleted clip file: {clip_path}")
            
            # Delete metadata file
            if metadata_path.exists():
                metadata_path.unlink()
                deleted_files.append(str(metadata_path))
                logger.info(f"🗑️ Deleted metadata file: {metadata_path}")
            
            # Clean up empty video directory
            if video_dir.exists() and not any(video_dir.iterdir()):
                video_dir.rmdir()
                logger.info(f"🗑️ Deleted empty video directory: {video_dir}")
            
            return len(deleted_files) > 0
            
        except Exception as e:
            logger.error(f"❌ Failed to delete clip for video {video_id}, scene {scene_id}: {e}")
            return False
    
    def delete_video_clips(self, video_id: str) -> int:
        """
        Delete all clips for a specific video.
        
        Args:
            video_id: UUID of the video
            
        Returns:
            Number of clips deleted
        """
        try:
            deleted_count = 0
            
            # Find all video directories (could be in different year/month folders)
            for year_dir in self.clips_path.iterdir():
                if not year_dir.is_dir():
                    continue
                    
                for month_dir in year_dir.iterdir():
                    if not month_dir.is_dir():
                        continue
                        
                    video_dir = month_dir / video_id
                    if video_dir.exists():
                        # Delete all files in video directory
                        for file_path in video_dir.iterdir():
                            if file_path.is_file():
                                file_path.unlink()
                                deleted_count += 1
                                logger.info(f"🗑️ Deleted file: {file_path}")
                        
                        # Remove empty directory
                        video_dir.rmdir()
                        logger.info(f"🗑️ Deleted video directory: {video_dir}")
            
            logger.info(f"🗑️ Deleted {deleted_count} files for video {video_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Failed to delete clips for video {video_id}: {e}")
            return 0
    
    def get_clip_metadata(self, video_id: str, scene_id: str, scene_index: int) -> Optional[Dict]:
        """
        Get metadata for a specific clip.
        
        Args:
            video_id: UUID of the video
            scene_id: UUID of the scene
            scene_index: Index of the scene
            
        Returns:
            Clip metadata if found, None otherwise
        """
        try:
            video_dir = self.get_video_clip_directory(video_id)
            metadata_path = video_dir / f"scene_{scene_index:03d}_{scene_id[:8]}_metadata.json"
            
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    return json.load(f)
            else:
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to get metadata for video {video_id}, scene {scene_id}: {e}")
            return None
    
    def validate_clip_file(self, clip_path: str) -> bool:
        """
        Validate that a clip file exists and is readable.
        
        Args:
            clip_path: Path to the clip file
            
        Returns:
            True if file is valid, False otherwise
        """
        try:
            path = Path(clip_path)
            if not path.exists():
                logger.warning(f"⚠️ Clip file does not exist: {clip_path}")
                return False
            
            # Check file size
            file_size = path.stat().st_size
            if file_size == 0:
                logger.warning(f"⚠️ Clip file is empty: {clip_path}")
                return False
            
            # Check if file is readable
            with open(path, 'rb') as f:
                f.read(1024)  # Read first 1KB to test readability
            
            logger.debug(f"✅ Clip file validated: {clip_path} ({file_size} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to validate clip file {clip_path}: {e}")
            return False
    
    def cleanup_temp_files(self) -> int:
        """
        Clean up temporary files in the temp directory.
        
        Returns:
            Number of files cleaned up
        """
        try:
            cleaned_count = 0
            
            if self.temp_path.exists():
                for file_path in self.temp_path.iterdir():
                    if file_path.is_file():
                        file_size = file_path.stat().st_size
                        
                        # Delete files older than 1 hour or larger than max size
                        file_age = datetime.now().timestamp() - file_path.stat().st_mtime
                        if file_age > 3600 or file_size > self.max_file_size_mb:
                            file_path.unlink()
                            cleaned_count += 1
                            logger.info(f"🧹 Cleaned up temp file: {file_path}")
            
            if cleaned_count > 0:
                logger.info(f"🧹 Cleaned up {cleaned_count} temporary files")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup temp files: {e}")
            return 0
    
    def get_storage_stats(self) -> Dict[str, any]:
        """
        Get storage statistics.
        
        Returns:
            Dict with storage statistics
        """
        try:
            total_size = 0
            total_files = 0
            video_count = 0
            
            # Walk through clips directory
            for root, dirs, files in os.walk(self.clips_path):
                for file in files:
                    if file.endswith('.mp4'):
                        file_path = Path(root) / file
                        file_size = file_path.stat().st_size
                        total_size += file_size
                        total_files += 1
                
                # Count video directories
                if any(f.endswith('.mp4') for f in files):
                    video_count += 1
            
            return {
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024),
                "total_files": total_files,
                "video_count": video_count,
                "storage_path": str(self.base_storage_path)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get storage stats: {e}")
            return {
                "error": str(e),
                "storage_path": str(self.base_storage_path)
            }


# Global clip storage instance
_clip_storage = None

def get_clip_storage() -> ClipStorage:
    """Get the global clip storage instance."""
    global _clip_storage
    if _clip_storage is None:
        _clip_storage = ClipStorage()
    return _clip_storage 