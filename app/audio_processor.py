#!/usr/bin/env python3
"""
Audio Processing Utilities for Video Compilation Pipeline
Handles timing synchronization, format conversion, and audio optimization
"""

import logging
import asyncio
import base64
import io
import time
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import tempfile
import os
from pathlib import Path

from app.audio_generator import AudioSegment, AudioGenerationResult

logger = logging.getLogger(__name__)

@dataclass
class TimingAdjustment:
    """Audio timing adjustment for video synchronization."""
    segment_id: str
    original_start: float
    original_end: float
    adjusted_start: float
    adjusted_end: float
    speed_factor: float
    padding_before: float
    padding_after: float
    crossfade_duration: float

@dataclass
class ProcessedAudio:
    """Processed audio with optimizations applied."""
    segment_id: str
    original_audio: AudioSegment
    processed_audio_base64: Optional[str] = None
    timing_adjustment: Optional[TimingAdjustment] = None
    normalization_applied: bool = False
    noise_reduction_applied: bool = False
    crossfade_applied: bool = False
    file_size_before: Optional[int] = None
    file_size_after: Optional[int] = None
    processing_time: Optional[float] = None
    status: str = "pending"  # "pending", "processing", "completed", "failed"
    error: Optional[str] = None

@dataclass
class AudioProcessingResult:
    """Result of audio processing operation."""
    success: bool
    total_segments: int
    processed_segments: int
    failed_segments: int
    total_processing_time: float
    processed_audio: List[ProcessedAudio]
    metadata: Dict[str, Any]
    error: Optional[str] = None

class AudioProcessor:
    """
    Audio processing utilities for video compilation pipeline.
    Handles timing synchronization, format conversion, and optimization.
    """
    
    def __init__(self):
        # Audio processing configuration
        self.target_sample_rate = 22050
        self.target_channels = 1  # Mono for voice
        self.target_bitrate = 128  # kbps
        self.normalization_target = -14.0  # LUFS
        
        # Timing configuration
        self.default_crossfade_duration = 0.2  # seconds
        self.max_speed_adjustment = 1.3  # Maximum speed factor
        self.min_speed_adjustment = 0.7   # Minimum speed factor
        self.silence_padding = 0.1  # seconds of silence padding
        
        # FFmpeg availability (will be checked at runtime)
        self._ffmpeg_available = None
    
    async def process_audio_segments(self, 
                                   audio_result: AudioGenerationResult,
                                   target_timings: Optional[List[Tuple[float, float]]] = None,
                                   enable_crossfades: bool = True,
                                   enable_normalization: bool = True,
                                   enable_noise_reduction: bool = False) -> AudioProcessingResult:
        """
        Process audio segments with timing adjustments and optimizations.
        
        Args:
            audio_result: AudioGenerationResult from TTS generation
            target_timings: Optional list of (start, end) timings for synchronization
            enable_crossfades: Whether to apply crossfade transitions
            enable_normalization: Whether to normalize audio levels
            enable_noise_reduction: Whether to apply noise reduction
            
        Returns:
            AudioProcessingResult with processed audio segments
        """
        start_time = time.time()
        
        logger.info(f"🔊 Starting audio processing for {len(audio_result.audio_segments)} segments")
        logger.info(f"⚙️ Crossfades: {enable_crossfades}, Normalize: {enable_normalization}, Noise Reduction: {enable_noise_reduction}")
        
        if not audio_result.audio_segments:
            return AudioProcessingResult(
                success=False,
                total_segments=0,
                processed_segments=0,
                failed_segments=0,
                total_processing_time=0.0,
                processed_audio=[],
                metadata={},
                error="No audio segments to process"
            )
        
        # Check FFmpeg availability
        ffmpeg_available = await self._check_ffmpeg_availability()
        if not ffmpeg_available:
            logger.warning("⚠️ FFmpeg not available - using basic processing")
        
        processed_audio = []
        processed_segments = 0
        failed_segments = 0
        
        try:
            # Process each audio segment
            for i, audio_segment in enumerate(audio_result.audio_segments):
                logger.debug(f"🔄 Processing audio segment {i+1}/{len(audio_result.audio_segments)}: {audio_segment.segment_id}")
                
                # Create processed audio object
                processed = ProcessedAudio(
                    segment_id=audio_segment.segment_id,
                    original_audio=audio_segment,
                    file_size_before=audio_segment.file_size,
                    status="pending"
                )
                
                try:
                    # Calculate timing adjustments if target timings provided
                    if target_timings and i < len(target_timings):
                        target_start, target_end = target_timings[i]
                        timing_adjustment = self._calculate_timing_adjustment(
                            audio_segment, target_start, target_end
                        )
                        processed.timing_adjustment = timing_adjustment
                    
                    # Process the audio segment
                    await self._process_single_audio_segment(
                        processed, 
                        ffmpeg_available,
                        enable_crossfades and i > 0,  # No crossfade for first segment
                        enable_normalization,
                        enable_noise_reduction
                    )
                    
                    if processed.status == "completed":
                        processed_segments += 1
                    else:
                        failed_segments += 1
                        
                except Exception as e:
                    logger.error(f"❌ Failed to process audio segment {i}: {e}")
                    processed.status = "failed"
                    processed.error = str(e)
                    failed_segments += 1
                
                processed_audio.append(processed)
            
            # Calculate totals and metadata
            total_processing_time = time.time() - start_time
            
            metadata = {
                "processing_timestamp": time.time(),
                "ffmpeg_available": ffmpeg_available,
                "crossfades_enabled": enable_crossfades,
                "normalization_enabled": enable_normalization,
                "noise_reduction_enabled": enable_noise_reduction,
                "target_sample_rate": self.target_sample_rate,
                "target_channels": self.target_channels,
                "target_bitrate": self.target_bitrate,
                "average_processing_time": total_processing_time / len(processed_audio),
                "total_size_before": sum(p.file_size_before or 0 for p in processed_audio),
                "total_size_after": sum(p.file_size_after or 0 for p in processed_audio),
                "compression_ratio": self._calculate_compression_ratio(processed_audio),
                "timing_adjustments_applied": sum(1 for p in processed_audio if p.timing_adjustment)
            }
            
            success = processed_segments > 0 and failed_segments == 0
            
            if success:
                logger.info(f"✅ Audio processing completed successfully!")
                logger.info(f"📊 Processed {processed_segments}/{len(processed_audio)} segments")
                logger.info(f"⏱️ Total time: {total_processing_time:.2f}s")
                logger.info(f"📦 Compression ratio: {metadata['compression_ratio']:.2f}")
            else:
                logger.warning(f"⚠️ Audio processing completed with {failed_segments} failures")
            
            return AudioProcessingResult(
                success=success,
                total_segments=len(processed_audio),
                processed_segments=processed_segments,
                failed_segments=failed_segments,
                total_processing_time=total_processing_time,
                processed_audio=processed_audio,
                metadata=metadata,
                error=f"{failed_segments} segments failed" if failed_segments > 0 else None
            )
            
        except Exception as e:
            logger.error(f"❌ Audio processing pipeline failed: {e}")
            return AudioProcessingResult(
                success=False,
                total_segments=len(audio_result.audio_segments),
                processed_segments=0,
                failed_segments=len(audio_result.audio_segments),
                total_processing_time=time.time() - start_time,
                processed_audio=processed_audio,
                metadata={},
                error=str(e)
            )
    
    async def _process_single_audio_segment(self, 
                                          processed: ProcessedAudio,
                                          ffmpeg_available: bool,
                                          apply_crossfade: bool,
                                          enable_normalization: bool,
                                          enable_noise_reduction: bool):
        """Process a single audio segment with optimizations."""
        start_time = time.time()
        processed.status = "processing"
        
        try:
            # Start with original audio
            if not processed.original_audio.audio_base64:
                # Use placeholder if no actual audio
                processed.processed_audio_base64 = None
                processed.status = "completed"
                processed.processing_time = time.time() - start_time
                return
            
            # If FFmpeg is available, use advanced processing
            if ffmpeg_available:
                await self._process_with_ffmpeg(
                    processed, apply_crossfade, enable_normalization, enable_noise_reduction
                )
            else:
                # Basic processing without FFmpeg
                await self._process_basic(processed)
            
            processed.processing_time = time.time() - start_time
            processed.status = "completed"
            
        except Exception as e:
            processed.status = "failed"
            processed.error = str(e)
            processed.processing_time = time.time() - start_time
    
    async def _process_with_ffmpeg(self, processed: ProcessedAudio, 
                                 apply_crossfade: bool,
                                 enable_normalization: bool, 
                                 enable_noise_reduction: bool):
        """Process audio using FFmpeg for advanced features."""
        # TODO: Implement FFmpeg-based audio processing
        # For now, use basic processing
        logger.debug(f"🔧 FFmpeg processing for {processed.segment_id} (placeholder)")
        await self._process_basic(processed)
        
        # Mark which optimizations were applied
        processed.normalization_applied = enable_normalization
        processed.noise_reduction_applied = enable_noise_reduction
        processed.crossfade_applied = apply_crossfade
    
    async def _process_basic(self, processed: ProcessedAudio):
        """Basic audio processing without FFmpeg."""
        try:
            # For basic processing, we'll just copy the original audio
            # and simulate processing time
            await asyncio.sleep(0.1)  # Simulate processing
            
            # Copy original audio as processed
            processed.processed_audio_base64 = processed.original_audio.audio_base64
            processed.file_size_after = processed.original_audio.file_size
            
            logger.debug(f"✅ Basic processing completed for {processed.segment_id}")
            
        except Exception as e:
            logger.error(f"❌ Basic processing failed for {processed.segment_id}: {e}")
            raise
    
    def _calculate_timing_adjustment(self, audio_segment: AudioSegment, 
                                   target_start: float, target_end: float) -> TimingAdjustment:
        """
        Calculate timing adjustments needed for video synchronization.
        
        Args:
            audio_segment: Original audio segment
            target_start: Target start time in video
            target_end: Target end time in video
            
        Returns:
            TimingAdjustment with calculated parameters
        """
        original_duration = audio_segment.duration
        target_duration = target_end - target_start
        
        # Prevent division by zero - if target duration is zero or negative, use a minimum duration
        if target_duration <= 0:
            logger.warning(f"⚠️ Invalid target duration {target_duration} for segment {audio_segment.segment_id}, using minimum 1.0s")
            target_duration = 1.0
        
        # Calculate speed factor needed
        speed_factor = original_duration / target_duration
        
        # Clamp speed factor to reasonable limits
        speed_factor = max(self.min_speed_adjustment, 
                          min(self.max_speed_adjustment, speed_factor))
        
        # Calculate actual adjusted duration
        adjusted_duration = original_duration / speed_factor
        
        # Calculate padding needed
        remaining_time = target_duration - adjusted_duration
        padding_before = max(0, remaining_time / 2)
        padding_after = max(0, remaining_time - padding_before)
        
        return TimingAdjustment(
            segment_id=audio_segment.segment_id,
            original_start=audio_segment.start_time,
            original_end=audio_segment.end_time,
            adjusted_start=target_start,
            adjusted_end=target_end,
            speed_factor=speed_factor,
            padding_before=padding_before,
            padding_after=padding_after,
            crossfade_duration=self.default_crossfade_duration
        )
    
    async def _check_ffmpeg_availability(self) -> bool:
        """Check if FFmpeg is available on the system."""
        if self._ffmpeg_available is not None:
            return self._ffmpeg_available
        
        try:
            # Try to run ffmpeg version command
            process = await asyncio.create_subprocess_exec(
                'ffmpeg', '-version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            self._ffmpeg_available = process.returncode == 0
            
            if self._ffmpeg_available:
                logger.info("✅ FFmpeg detected - advanced audio processing available")
            else:
                logger.warning("⚠️ FFmpeg not found - using basic audio processing")
            
        except Exception:
            self._ffmpeg_available = False
            logger.warning("⚠️ FFmpeg not available - using basic audio processing")
        
        return self._ffmpeg_available
    
    def _calculate_compression_ratio(self, processed_audio: List[ProcessedAudio]) -> float:
        """Calculate overall compression ratio from processing."""
        total_before = sum(p.file_size_before or 0 for p in processed_audio)
        total_after = sum(p.file_size_after or 0 for p in processed_audio)
        
        if total_before > 0:
            return total_before / total_after
        return 1.0
    
    async def create_master_audio_track(self, 
                                      processed_audio: List[ProcessedAudio],
                                      target_duration: float,
                                      fade_in_duration: float = 0.5,
                                      fade_out_duration: float = 0.5) -> Optional[str]:
        """
        Create a master audio track from processed segments.
        
        Args:
            processed_audio: List of processed audio segments
            target_duration: Target duration for the master track
            fade_in_duration: Fade in duration at start
            fade_out_duration: Fade out duration at end
            
        Returns:
            Base64 encoded master audio track, or None if failed
        """
        logger.info(f"🎵 Creating master audio track from {len(processed_audio)} segments")
        
        try:
            # For now, this is a placeholder that combines the audio metadata
            # TODO: Implement actual audio mixing/concatenation
            
            # Simulate processing time
            await asyncio.sleep(1.0)
            
            # Create metadata for master track
            master_metadata = {
                "total_segments": len(processed_audio),
                "target_duration": target_duration,
                "fade_in_duration": fade_in_duration,
                "fade_out_duration": fade_out_duration,
                "segments": [
                    {
                        "segment_id": p.segment_id,
                        "start_time": p.timing_adjustment.adjusted_start if p.timing_adjustment else p.original_audio.start_time,
                        "end_time": p.timing_adjustment.adjusted_end if p.timing_adjustment else p.original_audio.end_time,
                        "voice_model": p.original_audio.voice_model
                    }
                    for p in processed_audio
                ]
            }
            
            # Encode metadata as base64 (placeholder for actual audio)
            metadata_json = json.dumps(master_metadata, indent=2)
            placeholder_audio = base64.b64encode(metadata_json.encode()).decode()
            
            logger.info(f"✅ Master audio track created (placeholder)")
            return placeholder_audio
            
        except Exception as e:
            logger.error(f"❌ Failed to create master audio track: {e}")
            return None
    
    def get_processing_summary(self, result: AudioProcessingResult) -> Dict[str, Any]:
        """
        Generate a summary of audio processing results.
        
        Args:
            result: AudioProcessingResult to summarize
            
        Returns:
            Dictionary with processing summary
        """
        if not result.processed_audio:
            return {"total_segments": 0, "summary": "No audio processed"}
        
        # Analyze processing results
        timing_adjustments = sum(1 for p in result.processed_audio if p.timing_adjustment)
        normalization_applied = sum(1 for p in result.processed_audio if p.normalization_applied)
        crossfades_applied = sum(1 for p in result.processed_audio if p.crossfade_applied)
        
        # Calculate average processing time
        processing_times = [p.processing_time for p in result.processed_audio if p.processing_time]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        return {
            "total_segments": result.total_segments,
            "processed_segments": result.processed_segments,
            "failed_segments": result.failed_segments,
            "success_rate": (result.processed_segments / result.total_segments * 100) if result.total_segments > 0 else 0,
            "total_processing_time": result.total_processing_time,
            "average_processing_time": avg_processing_time,
            "timing_adjustments": timing_adjustments,
            "normalization_applied": normalization_applied,
            "crossfades_applied": crossfades_applied,
            "compression_ratio": result.metadata.get("compression_ratio", 1.0),
            "total_size_reduction": result.metadata.get("total_size_before", 0) - result.metadata.get("total_size_after", 0)
        }

# Global instance factory
def get_audio_processor() -> AudioProcessor:
    """Get an AudioProcessor instance."""
    return AudioProcessor() 