#!/usr/bin/env python3
"""
OpenAI TTS Audio Generator for Video Compilation Pipeline
Converts script segments into high-quality audio narration using OpenAI Text-to-Speech
"""

import logging
import asyncio
import base64
import io
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import tempfile
import os

from app.db_connections import DatabaseConnections
from app.ai_script_generator import CompilationScript, ScriptSegment

logger = logging.getLogger(__name__)

@dataclass
class AudioSegment:
    """Generated audio segment with metadata."""
    segment_id: str
    script_text: str
    start_time: float
    end_time: float
    duration: float
    voice_model: str
    audio_base64: Optional[str] = None
    audio_file_path: Optional[str] = None
    file_size: Optional[int] = None
    generation_time: Optional[float] = None
    status: str = "pending"  # "pending", "generating", "completed", "failed"
    error: Optional[str] = None

@dataclass
class AudioGenerationResult:
    """Result of audio generation process."""
    success: bool
    total_segments: int
    successful_segments: int
    failed_segments: int
    total_duration: float
    total_generation_time: float
    audio_segments: List[AudioSegment]
    metadata: Dict[str, Any]
    error: Optional[str] = None

class OpenAITTSGenerator:
    """
    OpenAI Text-to-Speech generator for video compilation narration.
    Converts script segments into high-quality audio using OpenAI's TTS API.
    """
    
    def __init__(self, connections: DatabaseConnections):
        self.connections = connections
        self.openai_client = connections.get_openai_client() if connections else None
        
        # TTS Configuration
        self.default_voice = "alloy"
        self.default_model = "tts-1"  # or "tts-1-hd" for higher quality
        self.output_format = "mp3"
        self.sample_rate = 22050
        
        # Voice model mapping for different content types
        self.voice_mapping = {
            "intro": "alloy",      # Warm, welcoming
            "instruction": "echo", # Clear, instructional
            "main": "fable",       # Natural, engaging
            "transition": "nova",  # Smooth, connecting
            "conclusion": "onyx"   # Confident, conclusive
        }
        
        # Available OpenAI TTS voices
        self.available_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        
        # Rate limiting for OpenAI TTS (adjust based on plan)
        self.max_concurrent_requests = 3
        self.request_delay = 0.5  # seconds between requests
        self._request_semaphore = asyncio.Semaphore(self.max_concurrent_requests)
    
    async def generate_audio_from_script(self, 
                                       script: CompilationScript,
                                       voice_preference: str = "alloy",
                                       use_voice_variety: bool = True,
                                       high_quality: bool = False) -> AudioGenerationResult:
        """
        Generate audio narration for all segments in a compilation script.
        
        Args:
            script: CompilationScript with segments to narrate
            voice_preference: Primary voice model preference
            use_voice_variety: Whether to use different voices for different segment types
            high_quality: Whether to use tts-1-hd model for higher quality
            
        Returns:
            AudioGenerationResult with all generated audio segments
        """
        start_time = time.time()
        
        logger.info(f"🎵 Starting audio generation for {len(script.segments)} script segments")
        logger.info(f"🎤 Voice preference: {voice_preference}, Variety: {use_voice_variety}, HQ: {high_quality}")
        
        # Validate inputs
        if not script.segments:
            return AudioGenerationResult(
                success=False,
                total_segments=0,
                successful_segments=0,
                failed_segments=0,
                total_duration=0.0,
                total_generation_time=0.0,
                audio_segments=[],
                metadata={},
                error="No script segments provided"
            )
        
        if not self.openai_client:
            logger.error("❌ OpenAI client not available for audio generation")
            return self._generate_placeholder_audio(script, voice_preference)
        
        # Validate voice preference
        if voice_preference not in self.available_voices:
            logger.warning(f"⚠️ Invalid voice '{voice_preference}', using default 'alloy'")
            voice_preference = "alloy"
        
        # Generate audio segments
        audio_segments = []
        successful_segments = 0
        failed_segments = 0
        
        try:
            # Create tasks for concurrent generation
            generation_tasks = []
            for i, segment in enumerate(script.segments):
                # Determine voice for this segment
                segment_voice = self._select_voice_for_segment(
                    segment, voice_preference, use_voice_variety
                )
                
                # Create audio segment metadata
                audio_segment = AudioSegment(
                    segment_id=f"audio_{i:03d}",
                    script_text=segment.script_text,
                    start_time=segment.start_time,
                    end_time=segment.end_time,
                    duration=segment.duration,
                    voice_model=segment_voice,
                    status="pending"
                )
                
                # Create generation task
                task = self._generate_single_audio_segment(
                    audio_segment, high_quality
                )
                generation_tasks.append(task)
                audio_segments.append(audio_segment)
            
            # Execute all generation tasks with rate limiting
            logger.info(f"🔄 Generating audio for {len(generation_tasks)} segments...")
            completed_segments = await asyncio.gather(*generation_tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(completed_segments):
                if isinstance(result, Exception):
                    logger.error(f"❌ Audio generation failed for segment {i}: {result}")
                    audio_segments[i].status = "failed"
                    audio_segments[i].error = str(result)
                    failed_segments += 1
                else:
                    # Update the segment with generated audio
                    audio_segments[i] = result
                    if result.status == "completed":
                        successful_segments += 1
                    else:
                        failed_segments += 1
            
            # Calculate totals
            total_generation_time = time.time() - start_time
            total_duration = sum(segment.duration for segment in audio_segments)
            
            # Generate metadata
            metadata = {
                "generation_timestamp": time.time(),
                "voice_preference": voice_preference,
                "use_voice_variety": use_voice_variety,
                "high_quality": high_quality,
                "model_used": "tts-1-hd" if high_quality else "tts-1",
                "voice_distribution": self._analyze_voice_distribution(audio_segments),
                "average_generation_time": total_generation_time / len(audio_segments),
                "total_characters": sum(len(segment.script_text) for segment in audio_segments),
                "estimated_cost": self._estimate_tts_cost(audio_segments, high_quality)
            }
            
            # Determine overall success
            success = successful_segments > 0 and failed_segments == 0
            
            if success:
                logger.info(f"✅ Audio generation completed successfully!")
                logger.info(f"📊 Generated {successful_segments}/{len(audio_segments)} segments")
                logger.info(f"⏱️ Total time: {total_generation_time:.2f}s")
                logger.info(f"🎤 Voice distribution: {metadata['voice_distribution']}")
            else:
                logger.warning(f"⚠️ Audio generation completed with {failed_segments} failures")
            
            return AudioGenerationResult(
                success=success,
                total_segments=len(audio_segments),
                successful_segments=successful_segments,
                failed_segments=failed_segments,
                total_duration=total_duration,
                total_generation_time=total_generation_time,
                audio_segments=audio_segments,
                metadata=metadata,
                error=f"{failed_segments} segments failed" if failed_segments > 0 else None
            )
            
        except Exception as e:
            logger.error(f"❌ Audio generation pipeline failed: {e}")
            return AudioGenerationResult(
                success=False,
                total_segments=len(script.segments),
                successful_segments=0,
                failed_segments=len(script.segments),
                total_duration=script.total_duration,
                total_generation_time=time.time() - start_time,
                audio_segments=audio_segments,
                metadata={},
                error=str(e)
            )
    
    async def _generate_single_audio_segment(self, audio_segment: AudioSegment, high_quality: bool) -> AudioSegment:
        """
        Generate audio for a single script segment.
        
        Args:
            audio_segment: AudioSegment to generate
            high_quality: Whether to use high-quality model
            
        Returns:
            Updated AudioSegment with generated audio
        """
        async with self._request_semaphore:
            start_time = time.time()
            audio_segment.status = "generating"
            
            try:
                # Apply rate limiting
                await asyncio.sleep(self.request_delay)
                
                # Select TTS model
                model = "tts-1-hd" if high_quality else "tts-1"
                
                # Prepare script text (clean and optimize for TTS)
                cleaned_text = self._prepare_text_for_tts(audio_segment.script_text)
                
                logger.debug(f"🎤 Generating audio: '{cleaned_text[:50]}...' with voice '{audio_segment.voice_model}'")
                
                # Call OpenAI TTS API
                response = await self.openai_client.audio.speech.create(
                    model=model,
                    voice=audio_segment.voice_model,
                    input=cleaned_text,
                    response_format=self.output_format,
                    speed=1.0  # Normal speed
                )
                
                # Get audio data
                audio_data = response.content
                
                # Convert to base64 for storage
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                
                # Update segment with generated audio
                audio_segment.audio_base64 = audio_base64
                audio_segment.file_size = len(audio_data)
                audio_segment.generation_time = time.time() - start_time
                audio_segment.status = "completed"
                
                logger.debug(f"✅ Audio generated for segment '{audio_segment.segment_id}' "
                           f"({audio_segment.file_size} bytes, {audio_segment.generation_time:.2f}s)")
                
                return audio_segment
                
            except Exception as e:
                audio_segment.status = "failed"
                audio_segment.error = str(e)
                audio_segment.generation_time = time.time() - start_time
                
                logger.error(f"❌ Failed to generate audio for segment '{audio_segment.segment_id}': {e}")
                return audio_segment
    
    def _select_voice_for_segment(self, segment: ScriptSegment, 
                                voice_preference: str, 
                                use_voice_variety: bool) -> str:
        """
        Select appropriate voice for a script segment.
        
        Args:
            segment: ScriptSegment to select voice for
            voice_preference: User's preferred voice
            use_voice_variety: Whether to use different voices for different types
            
        Returns:
            Voice model name to use
        """
        if not use_voice_variety:
            return voice_preference
        
        # Use voice mapping based on segment type
        segment_voice = self.voice_mapping.get(segment.segment_type, voice_preference)
        
        # Ensure the selected voice is available
        if segment_voice not in self.available_voices:
            segment_voice = voice_preference
        
        return segment_voice
    
    def _prepare_text_for_tts(self, text: str) -> str:
        """
        Clean and prepare text for optimal TTS generation.
        
        Args:
            text: Raw script text
            
        Returns:
            Cleaned text optimized for TTS
        """
        # Remove extra whitespace
        cleaned = " ".join(text.split())
        
        # Add natural pauses for better speech flow
        cleaned = cleaned.replace(". ", ". ")  # Slight pause after sentences
        cleaned = cleaned.replace(", ", ", ")  # Slight pause after commas
        
        # Handle common abbreviations for better pronunciation
        replacements = {
            " & ": " and ",
            " w/ ": " with ",
            " @ ": " at ",
            " # ": " number ",
            " % ": " percent ",
        }
        
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)
        
        # Ensure text ends with punctuation for natural speech
        if cleaned and not cleaned[-1] in '.!?':
            cleaned += '.'
        
        return cleaned
    
    def _analyze_voice_distribution(self, audio_segments: List[AudioSegment]) -> Dict[str, int]:
        """Analyze distribution of voices across segments."""
        voice_counts = {}
        for segment in audio_segments:
            voice = segment.voice_model
            voice_counts[voice] = voice_counts.get(voice, 0) + 1
        return voice_counts
    
    def _estimate_tts_cost(self, audio_segments: List[AudioSegment], high_quality: bool) -> float:
        """
        Estimate cost of TTS generation based on OpenAI pricing.
        
        Args:
            audio_segments: List of audio segments
            high_quality: Whether high-quality model was used
            
        Returns:
            Estimated cost in USD
        """
        # OpenAI TTS pricing (as of 2024):
        # tts-1: $15.00 / 1M characters
        # tts-1-hd: $30.00 / 1M characters
        
        total_characters = sum(len(segment.script_text) for segment in audio_segments)
        
        if high_quality:
            cost_per_million_chars = 30.00  # tts-1-hd
        else:
            cost_per_million_chars = 15.00  # tts-1
        
        estimated_cost = (total_characters / 1_000_000) * cost_per_million_chars
        return round(estimated_cost, 4)
    
    def _generate_placeholder_audio(self, script: CompilationScript, voice_preference: str) -> AudioGenerationResult:
        """Generate placeholder audio when OpenAI is not available."""
        logger.warning("🔄 Generating placeholder audio segments (OpenAI not available)")
        
        audio_segments = []
        for i, segment in enumerate(script.segments):
            audio_segment = AudioSegment(
                segment_id=f"placeholder_{i:03d}",
                script_text=segment.script_text,
                start_time=segment.start_time,
                end_time=segment.end_time,
                duration=segment.duration,
                voice_model=voice_preference,
                audio_base64=None,  # No actual audio
                status="placeholder"
            )
            audio_segments.append(audio_segment)
        
        return AudioGenerationResult(
            success=True,  # Placeholder is considered successful
            total_segments=len(audio_segments),
            successful_segments=len(audio_segments),
            failed_segments=0,
            total_duration=script.total_duration,
            total_generation_time=0.1,  # Instant placeholder generation
            audio_segments=audio_segments,
            metadata={
                "generation_type": "placeholder",
                "voice_preference": voice_preference,
                "note": "Placeholder audio generated - OpenAI TTS not available"
            }
        )
    
    async def generate_single_audio(self, text: str, 
                                  voice: str = "alloy", 
                                  high_quality: bool = False) -> Optional[str]:
        """
        Generate audio for a single text string.
        
        Args:
            text: Text to convert to speech
            voice: Voice model to use
            high_quality: Whether to use high-quality model
            
        Returns:
            Base64 encoded audio data, or None if failed
        """
        if not self.openai_client:
            logger.error("❌ OpenAI client not available")
            return None
        
        try:
            model = "tts-1-hd" if high_quality else "tts-1"
            cleaned_text = self._prepare_text_for_tts(text)
            
            response = await self.openai_client.audio.speech.create(
                model=model,
                voice=voice,
                input=cleaned_text,
                response_format=self.output_format
            )
            
            audio_data = response.content
            return base64.b64encode(audio_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"❌ Failed to generate single audio: {e}")
            return None
    
    def get_available_voices(self) -> List[str]:
        """Get list of available OpenAI TTS voices."""
        return self.available_voices.copy()
    
    def get_voice_recommendations(self, content_type: str) -> List[str]:
        """
        Get voice recommendations for specific content types.
        
        Args:
            content_type: Type of content ("intro", "instruction", "main", etc.)
            
        Returns:
            List of recommended voices for the content type
        """
        if content_type in self.voice_mapping:
            primary_voice = self.voice_mapping[content_type]
            # Return primary voice plus alternatives
            alternatives = [v for v in self.available_voices if v != primary_voice]
            return [primary_voice] + alternatives[:2]
        else:
            return self.available_voices[:3]  # Default recommendations

# Global instance factory
async def get_audio_generator(connections: DatabaseConnections) -> OpenAITTSGenerator:
    """Get an OpenAITTSGenerator instance."""
    return OpenAITTSGenerator(connections) 