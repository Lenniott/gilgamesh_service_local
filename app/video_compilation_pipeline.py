#!/usr/bin/env python3
"""
Video Compilation Pipeline - Main Orchestrator
Coordinates the entire AI-powered video compilation process from user requirements to final video
"""

import logging
import time
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from app.db_connections import DatabaseConnections
from app.ai_requirements_generator import RequirementsGenerator
from app.compilation_search import CompilationSearchEngine
from app.ai_script_generator import ScriptGenerator, CompilationScript
from app.generated_video_operations import GeneratedVideoDatabase
from app.audio_generator import OpenAITTSGenerator, AudioGenerationResult
from app.audio_processor import AudioProcessor, AudioProcessingResult

logger = logging.getLogger(__name__)

@dataclass
class CompilationRequest:
    """Request model for video compilation."""
    context: str                              # "I'm creating a morning workout routine"
    requirements: str                         # "5 minutes, beginner-friendly, mobility focus"
    title: Optional[str] = None              # "Morning Mobility Routine"
    voice_preference: str = "alloy"          # OpenAI TTS voice
    resolution: str = "720p"                 # Output resolution
    max_duration: float = 600.0              # 10 minutes max
    include_base64: bool = False             # Return video in response

@dataclass
class CompilationResponse:
    """Response model for video compilation."""
    success: bool
    generated_video_id: Optional[str] = None
    duration: Optional[float] = None
    source_videos_used: Optional[int] = None
    processing_time: Optional[float] = None
    script: Optional[Dict[str, Any]] = None
    video_base64: Optional[str] = None       # If include_base64=True
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class CompilationPipeline:
    """
    Main video compilation pipeline orchestrator.
    Coordinates all components to create AI-generated video compilations.
    """
    
    def __init__(self):
        self.connections = None
        self.requirements_generator = None
        self.search_engine = None
        self.script_generator = None
        self.generated_video_db = None
        self.audio_generator = None
        self.audio_processor = None
    
    async def initialize(self):
        """Initialize all pipeline components."""
        try:
            # Initialize database connections
            self.connections = DatabaseConnections()
            await self.connections.connect_all()
            
            # Initialize pipeline components
            self.requirements_generator = RequirementsGenerator(self.connections)
            self.search_engine = CompilationSearchEngine(self.connections)
            self.script_generator = ScriptGenerator(self.connections)
            self.generated_video_db = GeneratedVideoDatabase(self.connections)
            self.audio_generator = OpenAITTSGenerator(self.connections)
            self.audio_processor = AudioProcessor()
            
            logger.info("✅ Compilation pipeline initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize compilation pipeline: {e}")
            return False
    
    async def process_compilation_request(self, request: CompilationRequest) -> CompilationResponse:
        """
        Main pipeline orchestrator - processes compilation request end-to-end.
        
        Args:
            request: CompilationRequest with user requirements
            
        Returns:
            CompilationResponse with results or error details
        """
        start_time = time.time()
        
        try:
            logger.info(f"🎬 Starting video compilation: {request.title or 'Untitled'}")
            logger.info(f"📋 Context: {request.context}")
            logger.info(f"📋 Requirements: {request.requirements}")
            
            # Step 1: Validate request
            validation_result = self._validate_compilation_request(request)
            if not validation_result["valid"]:
                return CompilationResponse(
                    success=False,
                    error=f"Invalid request: {', '.join(validation_result['errors'])}",
                    processing_time=time.time() - start_time
                )
            
            # Step 2: Generate search queries from user requirements
            logger.info("🔍 Generating search queries from requirements...")
            search_queries = await self.requirements_generator.generate_search_queries(
                request.context, request.requirements
            )
            
            if not search_queries:
                return CompilationResponse(
                    success=False,
                    error="Failed to generate search queries from requirements",
                    processing_time=time.time() - start_time
                )
            
            logger.info(f"✅ Generated {len(search_queries)} search queries")
            
            # Step 3: Search vector database for relevant content
            logger.info("🔎 Searching for relevant video content...")
            search_results = await self.search_engine.search_content_segments(search_queries)
            
            # Check if we have sufficient content
            total_matches = sum(len(result.matches) for result in search_results)
            if total_matches == 0:
                return CompilationResponse(
                    success=False,
                    error="No relevant video content found for the specified requirements",
                    processing_time=time.time() - start_time
                )
            
            logger.info(f"✅ Found {total_matches} relevant video segments")
            
            # Step 4: Generate script with video assignments
            logger.info("📝 Generating compilation script...")
            script = await self.script_generator.create_segmented_script(
                search_results=search_results,
                user_context=request.context,
                user_requirements=request.requirements,
                target_duration=min(request.max_duration, 600.0)  # Cap at 10 minutes
            )
            
            if not script.segments:
                return CompilationResponse(
                    success=False,
                    error="Failed to generate compilation script",
                    processing_time=time.time() - start_time
                )
            
            logger.info(f"✅ Generated script with {len(script.segments)} segments")
            
            # Step 5: Generate audio for script segments (placeholder for now)
            logger.info("🎵 Generating audio segments...")
            audio_segments = await self._generate_audio_segments(script, request.voice_preference)
            
            # Step 6: Extract and compose video segments (placeholder for now)
            logger.info("🎬 Composing final video...")
            composed_video = await self._compose_final_video(script, audio_segments, request.resolution)
            
            if not composed_video:
                return CompilationResponse(
                    success=False,
                    error="Failed to compose final video",
                    processing_time=time.time() - start_time
                )
            
            # Step 7: Save generated video to database
            logger.info("💾 Saving generated video to database...")
            video_title = request.title or self._generate_auto_title(request.context, request.requirements)
            
            generated_video_id = await self.generated_video_db.save_generated_video(
                video_base64=composed_video["video_base64"],
                script=script,
                title=video_title,
                user_context=request.context,
                user_requirements=request.requirements,
                audio_segments=audio_segments,
                voice_model=request.voice_preference,
                resolution=request.resolution,
                processing_time=time.time() - start_time,
                description=f"AI-generated compilation: {request.context}"
            )
            
            if not generated_video_id:
                return CompilationResponse(
                    success=False,
                    error="Failed to save generated video to database",
                    processing_time=time.time() - start_time
                )
            
            # Step 8: Prepare response
            processing_time = time.time() - start_time
            
            # Convert script to dictionary for response
            script_dict = {
                "total_duration": script.total_duration,
                "segments": [
                    {
                        "script_text": segment.script_text,
                        "start_time": segment.start_time,
                        "end_time": segment.end_time,
                        "assigned_video_id": segment.assigned_video_id,
                        "transition_type": segment.transition_type,
                        "segment_type": segment.segment_type
                    }
                    for segment in script.segments
                ]
            }
            
            logger.info(f"✅ Video compilation completed successfully in {processing_time:.2f}s")
            logger.info(f"📹 Generated video ID: {generated_video_id}")
            logger.info(f"⏱️ Duration: {script.total_duration:.1f}s")
            logger.info(f"🎬 Videos used: {script.unique_videos_used}")
            
            return CompilationResponse(
                success=True,
                generated_video_id=generated_video_id,
                duration=script.total_duration,
                source_videos_used=script.unique_videos_used,
                processing_time=processing_time,
                script=script_dict,
                video_base64=composed_video["video_base64"] if request.include_base64 else None,
                metadata={
                    "search_queries_generated": len(search_queries),
                    "content_matches_found": total_matches,
                    "script_segments": len(script.segments),
                    "audio_segments": len(audio_segments) if audio_segments else 0,
                    "title": video_title,
                    "resolution": request.resolution,
                    "voice_model": request.voice_preference
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Compilation pipeline failed: {e}")
            return CompilationResponse(
                success=False,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def _validate_compilation_request(self, request: CompilationRequest) -> Dict[str, Any]:
        """Validate compilation request parameters."""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Required fields
        if not request.context or not request.context.strip():
            validation_result["errors"].append("Context is required")
            validation_result["valid"] = False
        
        if not request.requirements or not request.requirements.strip():
            validation_result["errors"].append("Requirements are required")
            validation_result["valid"] = False
        
        # Length limits
        if len(request.context) > 500:
            validation_result["errors"].append("Context too long (max 500 characters)")
            validation_result["valid"] = False
        
        if len(request.requirements) > 1000:
            validation_result["errors"].append("Requirements too long (max 1000 characters)")
            validation_result["valid"] = False
        
        # Duration limits
        if request.max_duration < 30:
            validation_result["errors"].append("Duration too short (minimum 30 seconds)")
            validation_result["valid"] = False
        
        if request.max_duration > 600:
            validation_result["warnings"].append("Duration capped at 10 minutes")
        
        # Valid voice models
        valid_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        if request.voice_preference not in valid_voices:
            validation_result["errors"].append(f"Invalid voice preference. Must be one of: {', '.join(valid_voices)}")
            validation_result["valid"] = False
        
        # Valid resolutions
        valid_resolutions = ["480p", "720p", "1080p"]
        if request.resolution not in valid_resolutions:
            validation_result["errors"].append(f"Invalid resolution. Must be one of: {', '.join(valid_resolutions)}")
            validation_result["valid"] = False
        
        return validation_result
    
    async def _generate_audio_segments(self, script: CompilationScript, voice_model: str) -> List[Dict[str, Any]]:
        """
        Generate audio segments for script using OpenAI TTS.
        
        Args:
            script: CompilationScript with segments
            voice_model: OpenAI TTS voice model
            
        Returns:
            List of audio segment metadata
        """
        logger.info(f"🎵 Generating {len(script.segments)} audio segments with voice '{voice_model}'...")
        
        try:
            # Generate audio using OpenAI TTS
            audio_result = await self.audio_generator.generate_audio_from_script(
                script=script,
                voice_preference=voice_model,
                use_voice_variety=True,  # Use different voices for different segment types
                high_quality=False  # Use standard quality for faster generation
            )
            
            if not audio_result.success:
                logger.error(f"❌ Audio generation failed: {audio_result.error}")
                return self._create_placeholder_audio_segments(script, voice_model)
            
            # Process audio for optimization and timing
            target_timings = [(seg.start_time, seg.end_time) for seg in script.segments]
            processing_result = await self.audio_processor.process_audio_segments(
                audio_result=audio_result,
                target_timings=target_timings,
                enable_crossfades=True,
                enable_normalization=True,
                enable_noise_reduction=False  # Disable for speed
            )
            
            # Convert to expected format
            audio_segments = []
            for processed in processing_result.processed_audio:
                audio_segment = {
                    "segment_id": processed.segment_id,
                    "script_text": processed.original_audio.script_text,
                    "start_time": processed.original_audio.start_time,
                    "end_time": processed.original_audio.end_time,
                    "duration": processed.original_audio.duration,
                    "voice_model": processed.original_audio.voice_model,
                    "audio_base64": processed.processed_audio_base64 or processed.original_audio.audio_base64,
                    "file_size": processed.file_size_after or processed.original_audio.file_size,
                    "generation_time": processed.original_audio.generation_time,
                    "processing_time": processed.processing_time,
                    "status": processed.status,
                    "timing_adjustment": {
                        "speed_factor": processed.timing_adjustment.speed_factor,
                        "padding_before": processed.timing_adjustment.padding_before,
                        "padding_after": processed.timing_adjustment.padding_after
                    } if processed.timing_adjustment else None,
                    "optimizations": {
                        "normalization_applied": processed.normalization_applied,
                        "crossfade_applied": processed.crossfade_applied,
                        "noise_reduction_applied": processed.noise_reduction_applied
                    }
                }
                audio_segments.append(audio_segment)
            
            # Log generation summary
            successful_segments = sum(1 for seg in audio_segments if seg["status"] == "completed")
            total_generation_time = audio_result.total_generation_time + processing_result.total_processing_time
            estimated_cost = audio_result.metadata.get("estimated_cost", 0.0)
            
            logger.info(f"✅ Generated {successful_segments}/{len(audio_segments)} audio segments successfully")
            logger.info(f"⏱️ Total audio generation time: {total_generation_time:.2f}s")
            logger.info(f"💰 Estimated TTS cost: ${estimated_cost:.4f}")
            logger.info(f"🎤 Voice distribution: {audio_result.metadata.get('voice_distribution', {})}")
            
            return audio_segments
            
        except Exception as e:
            logger.error(f"❌ Audio generation pipeline failed: {e}")
            return self._create_placeholder_audio_segments(script, voice_model)
    
    def _create_placeholder_audio_segments(self, script: CompilationScript, voice_model: str) -> List[Dict[str, Any]]:
        """Create placeholder audio segments when generation fails."""
        logger.warning("🔄 Creating placeholder audio segments")
        
        audio_segments = []
        for i, segment in enumerate(script.segments):
            audio_segment = {
                "segment_id": f"placeholder_{i:03d}",
                "script_text": segment.script_text,
                "start_time": segment.start_time,
                "end_time": segment.end_time,
                "duration": segment.duration,
                "voice_model": voice_model,
                "audio_base64": None,  # No actual audio
                "file_size": 0,
                "generation_time": 0.0,
                "processing_time": 0.0,
                "status": "placeholder",
                "timing_adjustment": None,
                "optimizations": {
                    "normalization_applied": False,
                    "crossfade_applied": False,
                    "noise_reduction_applied": False
                }
            }
            audio_segments.append(audio_segment)
        
        return audio_segments
    
    async def _compose_final_video(self, script: CompilationScript, 
                                 audio_segments: List[Dict[str, Any]], 
                                 resolution: str) -> Optional[Dict[str, Any]]:
        """
        Compose final video from script segments and audio.
        
        Args:
            script: CompilationScript with video assignments
            audio_segments: Generated audio segments
            resolution: Target resolution
            
        Returns:
            Dictionary with composed video data
        """
        # TODO: Implement video composition using FFmpeg
        # For now, return placeholder composed video
        
        logger.info(f"🎬 Composing video with {len(script.segments)} segments at {resolution}...")
        
        # Simulate video composition
        await asyncio.sleep(2)  # Simulate processing time
        
        # Placeholder composed video
        composed_video = {
            "video_base64": "placeholder_video_base64_data",  # TODO: Generate actual video
            "duration": script.total_duration,
            "resolution": resolution,
            "file_size": 1024 * 1024,  # Placeholder 1MB
            "composition_metadata": {
                "segments_used": len(script.segments),
                "audio_segments": len(audio_segments),
                "unique_videos": script.unique_videos_used,
                "composition_method": "placeholder"
            }
        }
        
        logger.info(f"✅ Video composition completed (placeholder)")
        return composed_video
    
    def _generate_auto_title(self, context: str, requirements: str) -> str:
        """Generate automatic title from context and requirements."""
        # Extract key terms for title
        context_words = context.lower().split()
        requirements_words = requirements.lower().split()
        
        # Common title patterns
        if "workout" in context_words or "exercise" in requirements_words:
            if "morning" in context_words:
                return "Morning Workout Routine"
            elif "beginner" in requirements_words:
                return "Beginner Workout Compilation"
            else:
                return "Custom Workout Routine"
        
        if "mobility" in requirements_words or "stretch" in requirements_words:
            return "Mobility & Flexibility Routine"
        
        if "strength" in requirements_words:
            return "Strength Training Compilation"
        
        if "core" in requirements_words:
            return "Core Strengthening Routine"
        
        # Default title
        return "AI-Generated Fitness Compilation"
    
    async def get_compilation_status(self, compilation_id: str) -> Dict[str, Any]:
        """
        Get status of a compilation (for long-running operations).
        
        Args:
            compilation_id: Compilation ID to check
            
        Returns:
            Dictionary with compilation status
        """
        # TODO: Implement compilation status tracking
        # For now, return placeholder status
        
        return {
            "compilation_id": compilation_id,
            "status": "completed",  # "pending", "processing", "completed", "failed"
            "progress": 100,
            "estimated_completion": None,
            "current_step": "Video composition completed",
            "total_steps": 8
        }
    
    async def cleanup(self):
        """Cleanup pipeline resources."""
        try:
            if self.connections:
                await self.connections.close_all()
            logger.info("✅ Compilation pipeline cleanup completed")
        except Exception as e:
            logger.error(f"❌ Pipeline cleanup failed: {e}")

# Global pipeline instance
compilation_pipeline = CompilationPipeline()

async def get_compilation_pipeline() -> CompilationPipeline:
    """Get the global compilation pipeline instance."""
    if not compilation_pipeline.connections:
        await compilation_pipeline.initialize()
    return compilation_pipeline 