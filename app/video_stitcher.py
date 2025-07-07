#!/usr/bin/env python3
"""
Video Stitcher for Compilation Pipeline
Creates final video from compilation JSON with clip looping and audio sync.
"""

import logging
from typing import Dict, Any, List
from dataclasses import dataclass
import tempfile

from app.stitch_scenes import stitch_scenes_to_base64, SceneInput

logger = logging.getLogger(__name__)

@dataclass
class StitchingSettings:
    """Settings for video stitching."""
    aspect_ratio: str = "9:16"  # "square" or "9:16"
    framerate: int = 30
    audio_bitrate: str = "128k"
    video_codec: str = "libx264"
    loop_clips: bool = True  # Loop clips to match audio duration

@dataclass
class ComposedVideo:
    """Result of video stitching."""
    video_base64: str
    duration: float
    aspect_ratio: str
    file_size: int
    segments_processed: int
    clips_looped: Dict[str, int]  # How many times each clip was looped

class VideoStitcher:
    """
    Creates final video from compilation JSON.
    Handles clip looping, audio sync, and transitions.
    """
    
    def __init__(self):
        """Initialize the video stitcher."""
        pass
    
    def stitch_compilation(self, segments: List[Dict[str, Any]], aspect_ratio: str = "9:16") -> str:
        """
        Stitch together a compilation from segments.
        
        Args:
            segments: List of segments with video, audio, and script
            aspect_ratio: Target aspect ratio ("square" or "9:16")
            
        Returns:
            Base64 encoded final video
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            scene_inputs = []
            
            for i, segment in enumerate(segments):
                if not segment.get("video"):
                    continue
                    
                scene = SceneInput(
                    video=segment["video"],
                    video_id=segment["video_id"],
                    audio=segment.get("audio"),
                    show_debug=segment.get("show_debug", False)
                )
                scene_inputs.append(scene)
            
            if not scene_inputs:
                raise ValueError("No valid video segments found")
                
            # Stitch scenes together
            final_video = stitch_scenes_to_base64(scene_inputs)
            
            return final_video 

    async def stitch_compilation_video(self, compilation_json: Dict[str, Any], 
                                      settings: StitchingSettings) -> ComposedVideo:
        """
        Create final video from compilation JSON.
        
        Args:
            compilation_json: Complete compilation JSON with segments
            settings: Stitching settings
            
        Returns:
            ComposedVideo with base64 video and metadata
        """
        try:
            segments = compilation_json.get("segments", [])
            if not segments:
                raise ValueError("No segments found in compilation JSON")
            
            # Convert segments to SceneInput format
            scene_inputs = []
            clips_looped = {}
            
            for i, segment in enumerate(segments):
                clips = segment.get("clips", [])
                if not clips:
                    continue
                    
                # Use the first clip from each segment
                clip = clips[0]
                
                scene = SceneInput(
                    video=clip.get("video"),
                    video_id=clip.get("video_id", f"unknown_{i}"),
                    audio=segment.get("audio"),
                    show_debug=False  # Can be made configurable
                )
                scene_inputs.append(scene)
                clips_looped[scene.video_id] = 1  # Track looping
            
            if not scene_inputs:
                raise ValueError("No valid video clips found in segments")
            
            # Stitch the scenes together
            final_video_base64 = stitch_scenes_to_base64(scene_inputs)
            
            # Calculate total duration
            total_duration = compilation_json.get("total_duration", 0.0)
            
            # Estimate file size (rough approximation)
            video_bytes = len(final_video_base64) * 3 // 4  # base64 to bytes
            
            return ComposedVideo(
                video_base64=final_video_base64,
                duration=total_duration,
                aspect_ratio=settings.aspect_ratio,
                file_size=video_bytes,
                segments_processed=len(segments),
                clips_looped=clips_looped
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to stitch compilation video: {e}")
            raise 