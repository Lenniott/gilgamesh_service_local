#!/usr/bin/env python3
"""
Video Compositor
Combines video segments with generated audio to create final compilation videos
"""

import logging
import tempfile
import subprocess
import os
import base64
import asyncio
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from app.video_segment_extractor import VideoSegment
from app.ai_script_generator import CompilationScript

logger = logging.getLogger(__name__)

@dataclass
class CompositionSettings:
    """Configuration for video composition."""
    resolution: str = "720p"
    framerate: int = 30
    audio_bitrate: str = "128k"
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    transition_duration: float = 0.5  # seconds
    enable_crossfades: bool = True
    enable_transitions: bool = True
    preset: str = "medium"
    crf: str = "24"

@dataclass
class ComposedVideo:
    """Result of video composition."""
    video_base64: str
    duration: float
    resolution: str
    file_size: int
    composition_metadata: Dict[str, Any]

@dataclass
class VideoCompositionResult:
    """Result of video composition process."""
    success: bool
    composed_video: Optional[ComposedVideo] = None
    composition_time: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

class VideoCompositor:
    """
    Video composition engine that combines video segments with audio.
    Uses FFmpeg for professional video composition with transitions and effects.
    """
    
    def __init__(self):
        # Resolution mapping
        self.resolution_map = {
            "480p": {"width": 854, "height": 480},
            "720p": {"width": 1280, "height": 720},
            "1080p": {"width": 1920, "height": 1080}
        }
        
        # Temporary file management
        self.temp_files = []
        
        # Transition effects
        self.transition_effects = {
            "cut": None,  # No transition
            "fade": "fade",
            "crossfade": "crossfade",
            "slide": "slide",
            "wipe": "wipe"
        }
    
    async def compose_final_video(self, video_segments: List[VideoSegment], 
                                audio_segments: List[Dict[str, Any]], 
                                script: CompilationScript,
                                settings: CompositionSettings) -> VideoCompositionResult:
        """
        Compose final video from video segments and audio.
        
        Args:
            video_segments: List of extracted video segments
            audio_segments: List of generated audio segments
            script: Original compilation script
            settings: Composition settings
            
        Returns:
            VideoCompositionResult with composed video
        """
        start_time = asyncio.get_event_loop().time()
        
        logger.info(f"🎬 Starting video composition: {len(video_segments)} video segments, {len(audio_segments)} audio segments")
        logger.info(f"📊 Target resolution: {settings.resolution}, duration: {script.total_duration:.2f}s")
        
        try:
            # Validate inputs
            if not video_segments:
                return VideoCompositionResult(
                    success=False,
                    error="No video segments provided for composition",
                    composition_time=0.0
                )
            
            if not audio_segments:
                return VideoCompositionResult(
                    success=False,
                    error="No audio segments provided for composition",
                    composition_time=0.0
                )
            
            # Step 1: Prepare video segments
            logger.info("📁 Preparing video segments...")
            video_files = await self._prepare_video_segments(video_segments, settings)
            
            # Step 2: Prepare audio segments
            logger.info("🎵 Preparing audio segments...")
            audio_files = await self._prepare_audio_segments(audio_segments)
            
            # Step 3: Create video composition
            logger.info("🎬 Creating video composition...")
            composed_video_path = await self._compose_video_with_audio(
                video_files, audio_files, script, settings
            )
            
            if not composed_video_path or not os.path.exists(composed_video_path):
                return VideoCompositionResult(
                    success=False,
                    error="Failed to create composed video",
                    composition_time=asyncio.get_event_loop().time() - start_time
                )
            
            # Step 4: Encode final video to base64
            logger.info("📦 Encoding final video...")
            composed_video = await self._encode_final_video(composed_video_path, settings)
            
            if not composed_video:
                return VideoCompositionResult(
                    success=False,
                    error="Failed to encode final video",
                    composition_time=asyncio.get_event_loop().time() - start_time
                )
            
            composition_time = asyncio.get_event_loop().time() - start_time
            
            logger.info(f"✅ Video composition completed in {composition_time:.2f}s")
            logger.info(f"📊 Final video: {composed_video.duration:.2f}s, {composed_video.file_size} bytes")
            
            return VideoCompositionResult(
                success=True,
                composed_video=composed_video,
                composition_time=composition_time,
                metadata={
                    "video_segments_used": len(video_segments),
                    "audio_segments_used": len(audio_segments),
                    "composition_settings": settings.__dict__,
                    "resolution": settings.resolution,
                    "total_duration": script.total_duration
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Video composition failed: {e}")
            return VideoCompositionResult(
                success=False,
                error=str(e),
                composition_time=asyncio.get_event_loop().time() - start_time
            )
        
        finally:
            # Clean up temporary files
            await self._cleanup_temp_files()
    
    async def _prepare_video_segments(self, video_segments: List[VideoSegment], 
                                    settings: CompositionSettings) -> List[str]:
        """
        Prepare video segments for composition.
        
        Args:
            video_segments: List of VideoSegment objects
            settings: Composition settings
            
        Returns:
            List of paths to prepared video files
        """
        logger.info(f"📁 Preparing {len(video_segments)} video segments...")
        
        video_files = []
        
        for i, segment in enumerate(video_segments):
            try:
                # Decode video segment to temp file
                temp_video_path = await self._decode_video_segment(segment, i)
                
                # Normalize video segment (ensure consistent format)
                normalized_path = await self._normalize_video_segment(temp_video_path, i, settings)
                
                video_files.append(normalized_path)
                
                logger.debug(f"✅ Prepared video segment {i}: {segment.duration:.2f}s")
                
            except Exception as e:
                logger.error(f"❌ Failed to prepare video segment {i}: {e}")
                # Create a placeholder black video for failed segments
                placeholder_path = await self._create_placeholder_video(segment.duration, i, settings)
                video_files.append(placeholder_path)
        
        logger.info(f"✅ Prepared {len(video_files)} video files")
        return video_files
    
    async def _prepare_audio_segments(self, audio_segments: List[Dict[str, Any]]) -> List[str]:
        """
        Prepare audio segments for composition.
        
        Args:
            audio_segments: List of audio segment dictionaries
            
        Returns:
            List of paths to prepared audio files
        """
        logger.info(f"🎵 Preparing {len(audio_segments)} audio segments...")
        
        audio_files = []
        
        for i, segment in enumerate(audio_segments):
            try:
                # Decode audio segment to temp file
                temp_audio_path = await self._decode_audio_segment(segment, i)
                audio_files.append(temp_audio_path)
                
                logger.debug(f"✅ Prepared audio segment {i}: {segment.get('duration', 0):.2f}s")
                
            except Exception as e:
                logger.error(f"❌ Failed to prepare audio segment {i}: {e}")
                # Create a placeholder silent audio for failed segments
                placeholder_path = await self._create_placeholder_audio(segment.get('duration', 5.0), i)
                audio_files.append(placeholder_path)
        
        logger.info(f"✅ Prepared {len(audio_files)} audio files")
        return audio_files
    
    async def _compose_video_with_audio(self, video_files: List[str], audio_files: List[str], 
                                      script: CompilationScript, 
                                      settings: CompositionSettings) -> str:
        """
        Compose video with audio using FFmpeg.
        
        Args:
            video_files: List of normalized video file paths
            audio_files: List of audio file paths
            script: Compilation script
            settings: Composition settings
            
        Returns:
            Path to composed video file
        """
        logger.info(f"🎬 Composing video with {len(video_files)} video segments and {len(audio_files)} audio segments")
        
        try:
            # Create temporary output file
            temp_output_path = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name
            self.temp_files.append(temp_output_path)
            
            # Strategy: Use FFmpeg concat filter for seamless video composition
            if len(video_files) == 1:
                # Single video segment - just add audio
                composed_path = await self._compose_single_video_with_audio(
                    video_files[0], audio_files, temp_output_path, settings
                )
            else:
                # Multiple video segments - concatenate with transitions
                composed_path = await self._compose_multiple_videos_with_audio(
                    video_files, audio_files, temp_output_path, settings
                )
            
            return composed_path
            
        except Exception as e:
            logger.error(f"❌ Failed to compose video with audio: {e}")
            return None
    
    async def _compose_single_video_with_audio(self, video_file: str, audio_files: List[str], 
                                             output_path: str, settings: CompositionSettings) -> str:
        """
        Compose single video with audio track.
        
        Args:
            video_file: Path to video file
            audio_files: List of audio file paths
            output_path: Output path for composed video
            settings: Composition settings
            
        Returns:
            Path to composed video
        """
        try:
            # Concatenate audio files first
            audio_concat_path = await self._concatenate_audio_files(audio_files)
            
            # Compose video with audio
            cmd = [
                'ffmpeg', '-y',
                '-i', video_file,
                '-i', audio_concat_path,
                '-c:v', settings.video_codec,
                '-c:a', settings.audio_codec,
                '-preset', settings.preset,
                '-crf', settings.crf,
                '-b:a', settings.audio_bitrate,
                '-movflags', '+faststart',
                '-shortest',  # Match shortest stream
                output_path
            ]
            
            logger.debug(f"🔧 Single video composition command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"❌ Single video composition failed: {result.stderr}")
                return None
            
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Single video composition failed: {e}")
            return None
    
    async def _compose_multiple_videos_with_audio(self, video_files: List[str], audio_files: List[str], 
                                                output_path: str, settings: CompositionSettings) -> str:
        """
        Compose multiple videos with audio track using FFmpeg concat.
        
        Args:
            video_files: List of video file paths
            audio_files: List of audio file paths
            output_path: Output path for composed video
            settings: Composition settings
            
        Returns:
            Path to composed video
        """
        try:
            # Create concat files
            video_concat_path = await self._create_video_concat_file(video_files)
            audio_concat_path = await self._concatenate_audio_files(audio_files)
            
            # Compose video with audio
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', video_concat_path,
                '-i', audio_concat_path,
                '-c:v', settings.video_codec,
                '-c:a', settings.audio_codec,
                '-preset', settings.preset,
                '-crf', settings.crf,
                '-b:a', settings.audio_bitrate,
                '-movflags', '+faststart',
                '-shortest',  # Match shortest stream
                output_path
            ]
            
            logger.debug(f"🔧 Multiple video composition command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"❌ Multiple video composition failed: {result.stderr}")
                return None
            
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Multiple video composition failed: {e}")
            return None
    
    async def _create_video_concat_file(self, video_files: List[str]) -> str:
        """
        Create FFmpeg concat file for video segments.
        
        Args:
            video_files: List of video file paths
            
        Returns:
            Path to concat file
        """
        concat_file_path = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False).name
        self.temp_files.append(concat_file_path)
        
        with open(concat_file_path, 'w') as f:
            for video_file in video_files:
                f.write(f"file '{video_file}'\n")
        
        logger.debug(f"📄 Created video concat file: {concat_file_path}")
        return concat_file_path
    
    async def _concatenate_audio_files(self, audio_files: List[str]) -> str:
        """
        Concatenate audio files into single audio track.
        
        Args:
            audio_files: List of audio file paths
            
        Returns:
            Path to concatenated audio file
        """
        if len(audio_files) == 1:
            return audio_files[0]
        
        try:
            # Create temporary output file
            temp_audio_path = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False).name
            self.temp_files.append(temp_audio_path)
            
            # Create audio concat file
            audio_concat_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False).name
            self.temp_files.append(audio_concat_file)
            
            with open(audio_concat_file, 'w') as f:
                for audio_file in audio_files:
                    f.write(f"file '{audio_file}'\n")
            
            # Concatenate audio files
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', audio_concat_file,
                '-c:a', 'aac',
                '-b:a', '128k',
                temp_audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"❌ Audio concatenation failed: {result.stderr}")
                return audio_files[0]  # Fallback to first audio file
            
            logger.debug(f"✅ Concatenated {len(audio_files)} audio files")
            return temp_audio_path
            
        except Exception as e:
            logger.error(f"❌ Audio concatenation failed: {e}")
            return audio_files[0]  # Fallback to first audio file
    
    async def _decode_video_segment(self, segment: VideoSegment, index: int) -> str:
        """
        Decode video segment to temporary file.
        
        Args:
            segment: VideoSegment object
            index: Segment index
            
        Returns:
            Path to decoded video file
        """
        try:
            # Decode base64
            video_bytes = base64.b64decode(segment.video_base64)
            
            # Create temporary file
            temp_path = tempfile.NamedTemporaryFile(suffix=f'_segment_{index}.mp4', delete=False).name
            self.temp_files.append(temp_path)
            
            # Write video data
            with open(temp_path, 'wb') as f:
                f.write(video_bytes)
            
            logger.debug(f"📁 Decoded video segment {index}: {len(video_bytes)} bytes")
            return temp_path
            
        except Exception as e:
            logger.error(f"❌ Failed to decode video segment {index}: {e}")
            raise
    
    async def _decode_audio_segment(self, segment: Dict[str, Any], index: int) -> str:
        """
        Decode audio segment to temporary file.
        
        Args:
            segment: Audio segment dictionary
            index: Segment index
            
        Returns:
            Path to decoded audio file
        """
        try:
            audio_base64 = segment.get('audio_base64')
            if not audio_base64:
                # Create silent audio if no audio provided
                return await self._create_placeholder_audio(segment.get('duration', 5.0), index)
            
            # Decode base64
            audio_bytes = base64.b64decode(audio_base64)
            
            # Create temporary file
            temp_path = tempfile.NamedTemporaryFile(suffix=f'_audio_{index}.mp3', delete=False).name
            self.temp_files.append(temp_path)
            
            # Write audio data
            with open(temp_path, 'wb') as f:
                f.write(audio_bytes)
            
            logger.debug(f"🎵 Decoded audio segment {index}: {len(audio_bytes)} bytes")
            return temp_path
            
        except Exception as e:
            logger.error(f"❌ Failed to decode audio segment {index}: {e}")
            # Create silent audio as fallback
            return await self._create_placeholder_audio(segment.get('duration', 5.0), index)
    
    async def _normalize_video_segment(self, video_path: str, index: int, 
                                     settings: CompositionSettings) -> str:
        """
        Normalize video segment to consistent format.
        
        Args:
            video_path: Path to video file
            index: Segment index
            settings: Composition settings
            
        Returns:
            Path to normalized video file
        """
        try:
            # Create temporary output file
            temp_output_path = tempfile.NamedTemporaryFile(suffix=f'_norm_{index}.mp4', delete=False).name
            self.temp_files.append(temp_output_path)
            
            # Get target resolution
            res_config = self.resolution_map.get(settings.resolution, self.resolution_map["720p"])
            
            # Normalize video
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-vf', f'scale={res_config["width"]}:{res_config["height"]}:force_original_aspect_ratio=decrease,pad={res_config["width"]}:{res_config["height"]}:(ow-iw)/2:(oh-ih)/2',
                '-r', str(settings.framerate),
                '-c:v', settings.video_codec,
                '-preset', settings.preset,
                '-crf', settings.crf,
                '-c:a', settings.audio_codec,
                '-b:a', settings.audio_bitrate,
                temp_output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"❌ Video normalization failed for segment {index}: {result.stderr}")
                return video_path  # Return original if normalization fails
            
            logger.debug(f"✅ Normalized video segment {index}")
            return temp_output_path
            
        except Exception as e:
            logger.error(f"❌ Video normalization failed for segment {index}: {e}")
            return video_path  # Return original if normalization fails
    
    async def _create_placeholder_video(self, duration: float, index: int, 
                                      settings: CompositionSettings) -> str:
        """
        Create placeholder black video for failed segments.
        
        Args:
            duration: Duration in seconds
            index: Segment index
            settings: Composition settings
            
        Returns:
            Path to placeholder video file
        """
        try:
            temp_path = tempfile.NamedTemporaryFile(suffix=f'_placeholder_{index}.mp4', delete=False).name
            self.temp_files.append(temp_path)
            
            # Get target resolution
            res_config = self.resolution_map.get(settings.resolution, self.resolution_map["720p"])
            
            # Create black video
            cmd = [
                'ffmpeg', '-y',
                '-f', 'lavfi',
                '-i', f'color=black:size={res_config["width"]}x{res_config["height"]}:duration={duration}',
                '-c:v', settings.video_codec,
                '-preset', settings.preset,
                '-crf', settings.crf,
                temp_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"❌ Placeholder video creation failed: {result.stderr}")
                return None
            
            logger.debug(f"✅ Created placeholder video for segment {index}: {duration:.2f}s")
            return temp_path
            
        except Exception as e:
            logger.error(f"❌ Failed to create placeholder video: {e}")
            return None
    
    async def _create_placeholder_audio(self, duration: float, index: int) -> str:
        """
        Create placeholder silent audio for failed segments.
        
        Args:
            duration: Duration in seconds
            index: Segment index
            
        Returns:
            Path to placeholder audio file
        """
        try:
            temp_path = tempfile.NamedTemporaryFile(suffix=f'_silent_{index}.mp3', delete=False).name
            self.temp_files.append(temp_path)
            
            # Create silent audio
            cmd = [
                'ffmpeg', '-y',
                '-f', 'lavfi',
                '-i', f'anullsrc=channel_layout=mono:sample_rate=22050:duration={duration}',
                '-c:a', 'aac',
                '-b:a', '128k',
                temp_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"❌ Placeholder audio creation failed: {result.stderr}")
                return None
            
            logger.debug(f"✅ Created placeholder audio for segment {index}: {duration:.2f}s")
            return temp_path
            
        except Exception as e:
            logger.error(f"❌ Failed to create placeholder audio: {e}")
            return None
    
    async def _encode_final_video(self, video_path: str, settings: CompositionSettings) -> Optional[ComposedVideo]:
        """
        Encode final video to base64 and create ComposedVideo object.
        
        Args:
            video_path: Path to composed video file
            settings: Composition settings
            
        Returns:
            ComposedVideo object or None if encoding failed
        """
        try:
            # Get video metadata
            duration = await self._get_video_duration(video_path)
            file_size = os.path.getsize(video_path)
            
            # Read and encode video
            with open(video_path, 'rb') as f:
                video_bytes = f.read()
                video_base64 = base64.b64encode(video_bytes).decode('utf-8')
            
            # Create ComposedVideo object
            composed_video = ComposedVideo(
                video_base64=video_base64,
                duration=duration,
                resolution=settings.resolution,
                file_size=file_size,
                composition_metadata={
                    "video_codec": settings.video_codec,
                    "audio_codec": settings.audio_codec,
                    "preset": settings.preset,
                    "crf": settings.crf,
                    "framerate": settings.framerate,
                    "audio_bitrate": settings.audio_bitrate,
                    "original_file_size": file_size
                }
            )
            
            logger.debug(f"📦 Encoded final video: {duration:.2f}s, {file_size} bytes")
            return composed_video
            
        except Exception as e:
            logger.error(f"❌ Failed to encode final video: {e}")
            return None
    
    async def _get_video_duration(self, video_path: str) -> float:
        """
        Get video duration using FFprobe.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Video duration in seconds
        """
        try:
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"❌ FFprobe failed: {result.stderr}")
                return 0.0
            
            probe_data = json.loads(result.stdout)
            duration = float(probe_data['format']['duration'])
            
            return duration
            
        except Exception as e:
            logger.error(f"❌ Failed to get video duration: {e}")
            return 0.0
    
    async def _cleanup_temp_files(self):
        """Clean up all temporary files."""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                logger.warning(f"⚠️ Failed to cleanup temp file {temp_file}: {e}")
        
        self.temp_files.clear() 