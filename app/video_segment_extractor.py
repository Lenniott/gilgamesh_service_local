#!/usr/bin/env python3
"""
Video Segment Extractor
Extracts precise video segments from existing base64 videos for compilation pipeline
"""

import logging
import tempfile
import subprocess
import os
import base64
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.ai_script_generator import CompilationScript, ScriptSegment
from app.simple_db_operations import SimpleDBOperations

logger = logging.getLogger(__name__)

@dataclass
class VideoSegment:
    """Represents an extracted video segment."""
    segment_id: str
    video_base64: str
    start_time: float
    end_time: float
    duration: float
    source_video_id: str
    resolution: str
    file_size: int
    extraction_metadata: Dict[str, Any]

@dataclass
class VideoSegmentExtractionResult:
    """Result of video segment extraction process."""
    success: bool
    segments: List[VideoSegment]
    total_segments: int
    successful_extractions: int
    failed_extractions: int
    total_extraction_time: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

class VideoSegmentExtractor:
    """
    Extracts precise video segments from existing base64 videos.
    Uses existing video_processing.py functions and FFmpeg for segment extraction.
    """
    
    def __init__(self, db_operations: SimpleDBOperations):
        self.db_operations = db_operations
        
        # Extraction configuration
        self.target_resolutions = {
            "480p": 480,
            "720p": 720,
            "1080p": 1080
        }
        
        # FFmpeg settings
        self.ffmpeg_preset = "medium"
        self.ffmpeg_crf = "24"
        self.video_codec = "libx264"
        self.audio_codec = "aac"
        
        # Temporary file management
        self.temp_files = []
    
    async def extract_segments_from_script(self, script: CompilationScript, 
                                         target_resolution: str = "720p") -> VideoSegmentExtractionResult:
        """
        Extract video segments based on script segment assignments.
        
        Args:
            script: CompilationScript with video assignments
            target_resolution: Target resolution for extracted segments
            
        Returns:
            VideoSegmentExtractionResult with extracted segments
        """
        start_time = asyncio.get_event_loop().time()
        
        logger.info(f"🎬 Extracting {len(script.segments)} video segments at {target_resolution}")
        
        extracted_segments = []
        successful_extractions = 0
        failed_extractions = 0
        
        try:
            # Group segments by source video to optimize database queries
            segments_by_video = {}
            for segment in script.segments:
                if segment.assigned_video_id:
                    if segment.assigned_video_id not in segments_by_video:
                        segments_by_video[segment.assigned_video_id] = []
                    segments_by_video[segment.assigned_video_id].append(segment)
            
            logger.info(f"📊 Processing {len(segments_by_video)} unique source videos")
            
            # Process each source video
            for video_id, video_segments in segments_by_video.items():
                try:
                    # Get video base64 from database
                    video_base64 = await self.db_operations.get_video_base64(video_id)
                    if not video_base64:
                        logger.error(f"❌ No video data found for video {video_id}")
                        failed_extractions += len(video_segments)
                        continue
                    
                    logger.info(f"📹 Processing {len(video_segments)} segments from video {video_id}")
                    
                    # Extract segments from this video
                    video_extraction_result = await self._extract_segments_from_video(
                        video_base64=video_base64,
                        video_id=video_id,
                        segments=video_segments,
                        target_resolution=target_resolution
                    )
                    
                    extracted_segments.extend(video_extraction_result.segments)
                    successful_extractions += video_extraction_result.successful_extractions
                    failed_extractions += video_extraction_result.failed_extractions
                    
                except Exception as e:
                    logger.error(f"❌ Failed to process video {video_id}: {e}")
                    failed_extractions += len(video_segments)
                    continue
            
            total_extraction_time = asyncio.get_event_loop().time() - start_time
            
            # Sort segments by script order
            extracted_segments.sort(key=lambda seg: float(seg.segment_id.split('_')[-1]))
            
            logger.info(f"✅ Video segment extraction completed in {total_extraction_time:.2f}s")
            logger.info(f"📊 Results: {successful_extractions} successful, {failed_extractions} failed")
            
            return VideoSegmentExtractionResult(
                success=successful_extractions > 0,
                segments=extracted_segments,
                total_segments=len(script.segments),
                successful_extractions=successful_extractions,
                failed_extractions=failed_extractions,
                total_extraction_time=total_extraction_time,
                metadata={
                    "unique_source_videos": len(segments_by_video),
                    "target_resolution": target_resolution,
                    "ffmpeg_settings": {
                        "preset": self.ffmpeg_preset,
                        "crf": self.ffmpeg_crf,
                        "video_codec": self.video_codec,
                        "audio_codec": self.audio_codec
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Video segment extraction failed: {e}")
            return VideoSegmentExtractionResult(
                success=False,
                segments=[],
                total_segments=len(script.segments),
                successful_extractions=0,
                failed_extractions=len(script.segments),
                total_extraction_time=asyncio.get_event_loop().time() - start_time,
                error=str(e)
            )
        
        finally:
            # Clean up temporary files
            await self._cleanup_temp_files()
    
    async def _extract_segments_from_video(self, video_base64: str, video_id: str, 
                                         segments: List[ScriptSegment], 
                                         target_resolution: str) -> VideoSegmentExtractionResult:
        """
        Extract multiple segments from a single video.
        
        Args:
            video_base64: Base64 encoded video data
            video_id: Source video UUID
            segments: List of ScriptSegment objects to extract
            target_resolution: Target resolution for extraction
            
        Returns:
            VideoSegmentExtractionResult for this video
        """
        logger.info(f"🎯 Extracting {len(segments)} segments from video {video_id}")
        
        extracted_segments = []
        successful_extractions = 0
        failed_extractions = 0
        
        # Decode video to temporary file
        temp_video_path = None
        try:
            temp_video_path = await self._decode_video_to_temp_file(video_base64)
            
            # Get video duration for validation
            video_duration = await self._get_video_duration(temp_video_path)
            if video_duration <= 0:
                logger.error(f"❌ Invalid video duration: {video_duration}")
                return VideoSegmentExtractionResult(
                    success=False,
                    segments=[],
                    total_segments=len(segments),
                    successful_extractions=0,
                    failed_extractions=len(segments),
                    total_extraction_time=0.0,
                    error=f"Invalid video duration: {video_duration}"
                )
            
            logger.info(f"📊 Source video duration: {video_duration:.2f}s")
            
            # Extract each segment
            for i, segment in enumerate(segments):
                try:
                    # Validate segment timing
                    if not self._validate_segment_timing(segment, video_duration):
                        logger.warning(f"⚠️ Invalid segment timing for segment {i}: {segment.assigned_video_start}-{segment.assigned_video_end}")
                        failed_extractions += 1
                        continue
                    
                    # Extract segment
                    extracted_segment = await self._extract_single_segment(
                        temp_video_path=temp_video_path,
                        segment=segment,
                        segment_index=i,
                        video_id=video_id,
                        target_resolution=target_resolution
                    )
                    
                    if extracted_segment:
                        extracted_segments.append(extracted_segment)
                        successful_extractions += 1
                    else:
                        failed_extractions += 1
                        
                except Exception as e:
                    logger.error(f"❌ Failed to extract segment {i}: {e}")
                    failed_extractions += 1
                    continue
            
            return VideoSegmentExtractionResult(
                success=successful_extractions > 0,
                segments=extracted_segments,
                total_segments=len(segments),
                successful_extractions=successful_extractions,
                failed_extractions=failed_extractions,
                total_extraction_time=0.0  # Will be calculated by parent
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to process video {video_id}: {e}")
            return VideoSegmentExtractionResult(
                success=False,
                segments=[],
                total_segments=len(segments),
                successful_extractions=0,
                failed_extractions=len(segments),
                total_extraction_time=0.0,
                error=str(e)
            )
        
        finally:
            # Clean up video file
            if temp_video_path and os.path.exists(temp_video_path):
                try:
                    os.unlink(temp_video_path)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to cleanup temp video file: {e}")
    
    async def _extract_single_segment(self, temp_video_path: str, segment: ScriptSegment, 
                                    segment_index: int, video_id: str, 
                                    target_resolution: str) -> Optional[VideoSegment]:
        """
        Extract a single video segment using FFmpeg.
        
        Args:
            temp_video_path: Path to temporary video file
            segment: ScriptSegment to extract
            segment_index: Index for segment ID
            video_id: Source video UUID
            target_resolution: Target resolution
            
        Returns:
            VideoSegment or None if extraction failed
        """
        segment_id = f"segment_{segment_index:03d}"
        
        try:
            # Create temporary output file
            temp_output_path = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name
            self.temp_files.append(temp_output_path)
            
            # Calculate segment duration
            start_time = segment.assigned_video_start
            end_time = segment.assigned_video_end
            duration = end_time - start_time
            
            # Get target width for resolution
            target_width = self.target_resolutions.get(target_resolution, 720)
            
            # Build FFmpeg command
            cmd = [
                'ffmpeg', '-y',
                '-i', temp_video_path,
                '-ss', str(start_time),
                '-t', str(duration),
                '-vf', f'scale={target_width}:-2',
                '-c:v', self.video_codec,
                '-crf', self.ffmpeg_crf,
                '-preset', self.ffmpeg_preset,
                '-c:a', self.audio_codec,
                '-movflags', '+faststart',
                temp_output_path
            ]
            
            logger.debug(f"🔧 FFmpeg command: {' '.join(cmd)}")
            
            # Execute FFmpeg command
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"❌ FFmpeg extraction failed for segment {segment_index}: {result.stderr}")
                return None
            
            # Check if output file was created
            if not os.path.exists(temp_output_path) or os.path.getsize(temp_output_path) == 0:
                logger.error(f"❌ No output file created for segment {segment_index}")
                return None
            
            # Read and encode output file
            with open(temp_output_path, 'rb') as f:
                video_bytes = f.read()
                video_base64 = base64.b64encode(video_bytes).decode('utf-8')
            
            # Create VideoSegment
            video_segment = VideoSegment(
                segment_id=segment_id,
                video_base64=video_base64,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                source_video_id=video_id,
                resolution=target_resolution,
                file_size=len(video_bytes),
                extraction_metadata={
                    "ffmpeg_preset": self.ffmpeg_preset,
                    "ffmpeg_crf": self.ffmpeg_crf,
                    "target_width": target_width,
                    "original_segment_start": segment.start_time,
                    "original_segment_end": segment.end_time,
                    "script_text": segment.script_text
                }
            )
            
            logger.debug(f"✅ Extracted segment {segment_index}: {duration:.2f}s, {len(video_bytes)} bytes")
            
            return video_segment
            
        except Exception as e:
            logger.error(f"❌ Failed to extract segment {segment_index}: {e}")
            return None
        
        finally:
            # Clean up temp output file
            if temp_output_path and os.path.exists(temp_output_path):
                try:
                    os.unlink(temp_output_path)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to cleanup temp output file: {e}")
    
    async def _decode_video_to_temp_file(self, video_base64: str) -> str:
        """
        Decode base64 video to temporary file.
        
        Args:
            video_base64: Base64 encoded video data
            
        Returns:
            Path to temporary video file
        """
        try:
            # Decode base64
            video_bytes = base64.b64decode(video_base64)
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            temp_path = temp_file.name
            self.temp_files.append(temp_path)
            
            # Write video data
            with open(temp_path, 'wb') as f:
                f.write(video_bytes)
            
            logger.debug(f"📁 Decoded video to temp file: {temp_path} ({len(video_bytes)} bytes)")
            
            return temp_path
            
        except Exception as e:
            logger.error(f"❌ Failed to decode video to temp file: {e}")
            raise
    
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
            
            import json
            probe_data = json.loads(result.stdout)
            duration = float(probe_data['format']['duration'])
            
            return duration
            
        except Exception as e:
            logger.error(f"❌ Failed to get video duration: {e}")
            return 0.0
    
    def _validate_segment_timing(self, segment: ScriptSegment, video_duration: float) -> bool:
        """
        Validate segment timing against video duration.
        
        Args:
            segment: ScriptSegment to validate
            video_duration: Total video duration
            
        Returns:
            True if segment timing is valid
        """
        # Check if segment has assigned video timing
        if not hasattr(segment, 'assigned_video_start') or not hasattr(segment, 'assigned_video_end'):
            logger.warning(f"⚠️ Segment missing video timing: {segment}")
            return False
        
        start_time = segment.assigned_video_start
        end_time = segment.assigned_video_end
        
        # Validate timing bounds
        if start_time < 0 or end_time < 0:
            logger.warning(f"⚠️ Negative timing values: {start_time}-{end_time}")
            return False
        
        if start_time >= end_time:
            logger.warning(f"⚠️ Invalid timing order: {start_time}-{end_time}")
            return False
        
        if end_time > video_duration:
            logger.warning(f"⚠️ Segment extends beyond video duration: {end_time} > {video_duration}")
            return False
        
        # Check minimum duration
        if (end_time - start_time) < 0.5:
            logger.warning(f"⚠️ Segment too short: {end_time - start_time:.2f}s")
            return False
        
        return True
    
    async def _cleanup_temp_files(self):
        """Clean up all temporary files."""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                logger.warning(f"⚠️ Failed to cleanup temp file {temp_file}: {e}")
        
        self.temp_files.clear() 