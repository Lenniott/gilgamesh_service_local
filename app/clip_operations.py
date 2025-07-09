#!/usr/bin/env python3
"""
Clip Operations Module
Handles extracting video clips from source videos and validating clip files.
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple
import tempfile

logger = logging.getLogger(__name__)

def extract_clip_from_video(source_video_path: str, start_time: float, end_time: float, 
                           output_path: str, target_width: int = 480) -> Dict[str, any]:
    """
    Extract a clip from a video file using ffmpeg.
    
    Args:
        source_video_path: Path to the source video file
        start_time: Start time in seconds
        end_time: End time in seconds
        output_path: Path where the clip should be saved
        target_width: Target width for the clip (height will be scaled proportionally)
        
    Returns:
        Dict with clip information including file path, size, and duration
    """
    try:
        # Validate input parameters
        if not os.path.exists(source_video_path):
            raise ValueError(f"Source video file does not exist: {source_video_path}")
        
        if start_time < 0 or end_time < 0:
            raise ValueError("Start and end times must be positive")
        
        if start_time >= end_time:
            raise ValueError("Start time must be less than end time")
        
        duration = end_time - start_time
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Extract clip using ffmpeg
        cmd = [
            'ffmpeg', '-y',
            '-i', source_video_path,
            '-ss', str(start_time),
            '-t', str(duration),
            '-vf', f'scale={target_width}:-2',  # Scale width, maintain aspect ratio
            '-c:v', 'libx264',
            '-crf', '24',  # Good quality, reasonable file size
            '-preset', 'medium',
            '-movflags', '+faststart',
            '-an',  # No audio for clips
            output_path
        ]
        
        logger.info(f"🎬 Extracting clip: {start_time:.2f}s - {end_time:.2f}s from {source_video_path}")
        logger.debug(f"ffmpeg command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Get file size and validate the output
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            if file_size == 0:
                raise ValueError("Extracted clip file is empty")
            
            logger.info(f"✅ Clip extracted successfully: {output_path} ({file_size} bytes)")
            
            return {
                "output_path": output_path,
                "file_size": file_size,
                "duration": duration,
                "start_time": start_time,
                "end_time": end_time,
                "target_width": target_width,
                "success": True
            }
        else:
            raise ValueError("Clip extraction failed - output file not created")
            
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ ffmpeg failed to extract clip: {e}")
        logger.error(f"ffmpeg stderr: {e.stderr}")
        raise ValueError(f"Failed to extract clip: {e}")
        
    except Exception as e:
        logger.error(f"❌ Failed to extract clip: {e}")
        raise

def validate_clip_file(clip_path: str) -> Dict[str, any]:
    """
    Validate a clip file using ffprobe.
    
    Args:
        clip_path: Path to the clip file to validate
        
    Returns:
        Dict with validation results and file information
    """
    try:
        if not os.path.exists(clip_path):
            return {
                "valid": False,
                "error": "File does not exist",
                "clip_path": clip_path
            }
        
        # Get file size
        file_size = os.path.getsize(clip_path)
        if file_size == 0:
            return {
                "valid": False,
                "error": "File is empty",
                "clip_path": clip_path,
                "file_size": 0
            }
        
        # Use ffprobe to get video information
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,duration,codec_name',
            '-show_entries', 'format=duration',
            '-of', 'json',
            clip_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        import json
        probe_data = json.loads(result.stdout)
        
        # Extract video stream info
        streams = probe_data.get('streams', [])
        if not streams:
            return {
                "valid": False,
                "error": "No video streams found",
                "clip_path": clip_path,
                "file_size": file_size
            }
        
        video_stream = streams[0]
        width = video_stream.get('width', 0)
        height = video_stream.get('height', 0)
        codec = video_stream.get('codec_name', 'unknown')
        duration = video_stream.get('duration', 0)
        
        # Get format duration as fallback
        format_info = probe_data.get('format', {})
        format_duration = format_info.get('duration', 0)
        
        # Use the more reliable duration
        final_duration = float(duration) if duration else float(format_duration)
        
        return {
            "valid": True,
            "clip_path": clip_path,
            "file_size": file_size,
            "width": width,
            "height": height,
            "codec": codec,
            "duration": final_duration,
            "aspect_ratio": f"{width}:{height}" if width and height else "unknown"
        }
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ ffprobe failed to validate clip: {e}")
        return {
            "valid": False,
            "error": f"ffprobe failed: {e.stderr}",
            "clip_path": clip_path
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to validate clip file {clip_path}: {e}")
        return {
            "valid": False,
            "error": str(e),
            "clip_path": clip_path
        }

def get_clip_metadata(clip_path: str) -> Optional[Dict]:
    """
    Get detailed metadata for a clip file.
    
    Args:
        clip_path: Path to the clip file
        
    Returns:
        Dict with clip metadata or None if failed
    """
    try:
        validation_result = validate_clip_file(clip_path)
        if not validation_result.get("valid", False):
            logger.warning(f"⚠️ Cannot get metadata for invalid clip: {clip_path}")
            return None
        
        # Get additional metadata using ffprobe
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,duration,codec_name,bit_rate,r_frame_rate',
            '-show_entries', 'format=duration,size,bit_rate',
            '-of', 'json',
            clip_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        import json
        probe_data = json.loads(result.stdout)
        
        # Extract detailed information
        streams = probe_data.get('streams', [])
        format_info = probe_data.get('format', {})
        
        if streams:
            video_stream = streams[0]
            metadata = {
                "file_path": clip_path,
                "file_size": int(format_info.get('size', 0)),
                "width": int(video_stream.get('width', 0)),
                "height": int(video_stream.get('height', 0)),
                "codec": video_stream.get('codec_name', 'unknown'),
                "duration": float(video_stream.get('duration', 0)),
                "bit_rate": video_stream.get('bit_rate', 'unknown'),
                "frame_rate": video_stream.get('r_frame_rate', 'unknown'),
                "format_bit_rate": format_info.get('bit_rate', 'unknown'),
                "valid": True
            }
        else:
            metadata = {
                "file_path": clip_path,
                "file_size": int(format_info.get('size', 0)),
                "valid": False,
                "error": "No video streams found"
            }
        
        return metadata
        
    except Exception as e:
        logger.error(f"❌ Failed to get metadata for clip {clip_path}: {e}")
        return None

def extract_multiple_clips(source_video_path: str, clip_segments: list, 
                          output_dir: str, target_width: int = 480) -> list:
    """
    Extract multiple clips from a single video file.
    
    Args:
        source_video_path: Path to the source video file
        clip_segments: List of dicts with 'start_time', 'end_time', 'scene_id', 'scene_index'
        output_dir: Directory to save clips
        target_width: Target width for clips
        
    Returns:
        List of dicts with clip information
    """
    results = []
    
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        for segment in clip_segments:
            start_time = segment['start_time']
            end_time = segment['end_time']
            scene_id = segment['scene_id']
            scene_index = segment['scene_index']
            
            # Generate output filename
            output_filename = f"scene_{scene_index:03d}_{scene_id[:8]}.mp4"
            output_path = os.path.join(output_dir, output_filename)
            
            try:
                clip_result = extract_clip_from_video(
                    source_video_path, start_time, end_time, output_path, target_width
                )
                
                # Add segment info to result
                clip_result.update({
                    "scene_id": scene_id,
                    "scene_index": scene_index,
                    "segment": segment
                })
                
                results.append(clip_result)
                logger.info(f"✅ Extracted clip {scene_index}: {output_filename}")
                
            except Exception as e:
                logger.error(f"❌ Failed to extract clip {scene_index}: {e}")
                results.append({
                    "scene_id": scene_id,
                    "scene_index": scene_index,
                    "success": False,
                    "error": str(e),
                    "segment": segment
                })
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Failed to extract multiple clips: {e}")
        return []

def cleanup_invalid_clips(clip_paths: list) -> list:
    """
    Clean up invalid clip files.
    
    Args:
        clip_paths: List of clip file paths to check
        
    Returns:
        List of cleaned up file paths
    """
    cleaned_files = []
    
    for clip_path in clip_paths:
        try:
            validation_result = validate_clip_file(clip_path)
            
            if not validation_result.get("valid", False):
                logger.warning(f"🗑️ Removing invalid clip: {clip_path}")
                os.remove(clip_path)
                cleaned_files.append(clip_path)
                
        except Exception as e:
            logger.error(f"❌ Error checking clip {clip_path}: {e}")
    
    if cleaned_files:
        logger.info(f"🧹 Cleaned up {len(cleaned_files)} invalid clip files")
    
    return cleaned_files

def get_video_duration(video_path: str) -> float:
    """
    Get the duration of a video file using ffprobe.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Duration in seconds
    """
    try:
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration_str = result.stdout.strip()
        
        if not duration_str or duration_str == 'N/A':
            raise ValueError("Could not determine video duration")
        
        return float(duration_str)
        
    except Exception as e:
        logger.error(f"❌ Failed to get video duration for {video_path}: {e}")
        raise ValueError(f"Failed to get video duration: {e}")

def create_clip_thumbnail(clip_path: str, output_path: str, time_offset: float = 1.0) -> bool:
    """
    Create a thumbnail image from a video clip.
    
    Args:
        clip_path: Path to the video clip
        output_path: Path for the thumbnail image
        time_offset: Time offset in seconds for thumbnail extraction
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create output directory if needed
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        cmd = [
            'ffmpeg', '-y',
            '-i', clip_path,
            '-ss', str(time_offset),
            '-vframes', '1',
            '-vf', 'scale=320:-1',  # Scale to 320px width
            '-f', 'image2',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if os.path.exists(output_path):
            logger.info(f"✅ Created thumbnail: {output_path}")
            return True
        else:
            logger.error(f"❌ Thumbnail creation failed: {output_path}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to create thumbnail for {clip_path}: {e}")
        return False 