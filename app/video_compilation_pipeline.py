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
from app.ai_script_generator import AIScriptGenerator
from app.video_stitcher import VideoStitcher, StitchingSettings
# from app.generated_video_operations import GeneratedVideoDatabase  # TODO: Implement according to pipeline spec
from app.audio_generator import OpenAITTSGenerator, AudioGenerationResult
# from app.audio_processor import AudioProcessor, AudioProcessingResult  # Not part of new simplified architecture
# from app.video_segment_extractor import VideoSegmentExtractor  # Not part of new simplified architecture  
# from app.video_compositor import VideoCompositor, CompositionSettings  # Not part of new simplified architecture

logger = logging.getLogger(__name__)

@dataclass
class CompilationRequest:
    """Request model for video compilation."""
    context: str                              # "I'm creating a morning workout routine"
    requirements: str                         # "5 minutes, beginner-friendly, mobility focus"
    title: Optional[str] = None              # "Morning Mobility Routine"
    voice_preference: str = "alloy"          # OpenAI TTS voice
    aspect_ratio: str = "9:16"               # "square" or "9:16"
    max_duration: float = 600.0              # 10 minutes max
    include_base64: bool = False             # Return final video in response
    audio: bool = True                       # Include base64 audio in JSON (debugging)
    clips: bool = True                       # Include base64 clips in JSON (debugging)
    show_debug_overlay: bool = False         # Show video ID overlay for debugging
    text_only: bool = True                   # Default to text-only for cost reduction
    max_segments_per_video: int = 2          # Diversity control
    min_unique_videos: int = 3               # Diversity control

@dataclass
class CompilationResponse:
    """Response model for video compilation."""
    success: bool
    generated_video_id: Optional[str] = None
    duration: Optional[float] = None
    source_videos_used: Optional[int] = None
    processing_time: Optional[float] = None
    compilation_json: Optional[Dict[str, Any]] = None  # Complete JSON structure
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
        self.video_stitcher = None
        # self.generated_video_db = None  # TODO: Implement according to pipeline spec
    
    async def initialize(self):
        """Initialize all pipeline components."""
        try:
            # Initialize database connections
            self.connections = DatabaseConnections()
            await self.connections.connect_all()
            
            # Initialize the 4 core pipeline components according to new architecture
            self.requirements_generator = RequirementsGenerator(self.connections)
            self.search_engine = CompilationSearchEngine(self.connections)
            self.script_generator = AIScriptGenerator(self.connections)
            await self.script_generator.initialize()
            
            # Initialize video stitcher
            self.video_stitcher = VideoStitcher()
            
            # TODO: Initialize generated video database
            # self.generated_video_db = GeneratedVideoDatabase(self.connections)
            
            logger.info("✅ Compilation pipeline initialized successfully (simplified architecture)")
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
            
            # Step 2: Generate workout requirements from user input
            logger.info("📋 Generating workout requirements from user input...")
            workout_requirements = await self.script_generator.generate_workout_requirements(
                f"{request.context} {request.requirements}"
            )
            
            logger.info(f"✅ Generated workout requirements: {workout_requirements.get('workout_type', 'unknown')} workout")
            logger.info(f"📊 Target duration: {workout_requirements.get('target_duration', 0)} minutes")
            logger.info(f"🎯 Primary goals: {workout_requirements.get('primary_goals', [])}")
            
            # Step 3: Generate search queries based on workout requirements
            logger.info("🔍 Generating search queries from workout requirements...")
            search_queries = await self.requirements_generator.generate_search_queries_from_requirements(
                workout_requirements
            )
            
            if not search_queries:
                return CompilationResponse(
                    success=False,
                    error="Failed to generate search queries from workout requirements",
                    processing_time=time.time() - start_time
                )
            
            logger.info(f"✅ Generated {len(search_queries)} search queries")
            logger.info(f"🔍 Search queries: {search_queries}")
            
            # Step 4: Search vector database for relevant content
            logger.info("🔎 Searching for relevant video content...")
            search_results = await self.search_engine.search_content_segments(search_queries, max_results_per_query=30)
            
            # Check if we have sufficient content
            total_matches = sum(len(result.matches) for result in search_results)
            if total_matches == 0:
                return CompilationResponse(
                    success=False,
                    error="No relevant video content found for the specified requirements",
                    processing_time=time.time() - start_time
                )
            
            logger.info(f"✅ Found {total_matches} relevant video segments")
            
            # Step 4.5: Apply diversity optimization
            logger.info("🎯 Applying diversity optimization...")
            optimized_results = await self.search_engine.optimize_search_results(
                search_results, 
                target_duration=request.max_duration,
                max_videos_per_query=request.min_unique_videos
            )
            
            # Use optimized results for script generation
            content_matches = []
            for result in optimized_results:
                content_matches.extend(result.matches)
            
            logger.info(f"✅ Optimized to {len(content_matches)} diverse content matches")
            
            # Step 5: AI generates complete compilation JSON using workout requirements
            logger.info("🎬 Generating compilation JSON (script + clips + audio)...")
            segments = await self.script_generator.generate_compilation_json_with_requirements(
                content_matches=content_matches,
                workout_requirements=workout_requirements,
                user_requirements=request.requirements,
                include_audio=request.audio and not request.text_only,  # Skip audio if text_only
                include_clips=request.clips,
                aspect_ratio=request.aspect_ratio
            )
            
            if not segments:
                return CompilationResponse(
                    success=False,
                    error="Failed to generate compilation JSON",
                    processing_time=time.time() - start_time
                )
            
            logger.info(f"✅ Generated compilation JSON with {len(segments)} segments")
            
            # Calculate total duration and source videos used
            total_duration = sum(segment["duration"] for segment in segments)
            source_videos = set()
            for segment in segments:
                for clip in segment["clips"]:
                    source_videos.add(clip["video_id"])
            
            # Create complete compilation JSON
            compilation_json = {
                "segments": segments,
                "total_duration": total_duration,
                "aspect_ratio": request.aspect_ratio
            }
            
            # Step 5: Video stitcher creates final video (only if include_base64=True)
            final_video = None
            if request.include_base64:
                logger.info("🎬 Creating final video with stitcher...")
                try:
                    stitching_settings = StitchingSettings(
                        aspect_ratio=request.aspect_ratio,
                        framerate=30,
                        loop_clips=True
                    )
                    
                    final_video = await self.video_stitcher.stitch_compilation_video(
                        compilation_json,
                        stitching_settings
                    )
                    logger.info(f"✅ Final video created: {final_video.duration:.1f}s, {final_video.file_size/1024/1024:.1f}MB")
                except Exception as e:
                    logger.error(f"❌ Failed to create final video: {e}")
                    # Continue without final video
            
            # Step 6: Save to database  
            logger.info("💾 Saving compilation to database...")
            video_title = request.title or self._generate_auto_title(request.context, request.requirements)
            
            # TODO: Save to generated_videos table
            generated_video_id = "test-compilation-123"  # Placeholder until DB implemented
            
            # Return successful response
            return CompilationResponse(
                success=True,
                generated_video_id=generated_video_id,
                duration=final_video.duration if final_video else total_duration,
                source_videos_used=len(source_videos),
                processing_time=time.time() - start_time,
                compilation_json=compilation_json,
                video_base64=final_video.video_base64 if final_video else None,
                metadata={
                    "title": video_title,
                    "aspect_ratio": request.aspect_ratio,
                    "segments": len(segments),
                    "total_matches": total_matches,
                    "search_queries": len(search_queries)
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Compilation failed: {e}")
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
        
        # Valid aspect ratios
        valid_aspect_ratios = ["square", "9:16"]
        if request.aspect_ratio not in valid_aspect_ratios:
            validation_result["errors"].append(f"Invalid aspect ratio. Must be one of: {', '.join(valid_aspect_ratios)}")
            validation_result["valid"] = False
        
        return validation_result

    # ============================================================================
    # LEGACY METHODS REMOVED - NOT PART OF NEW SIMPLIFIED ARCHITECTURE  
    # The new architecture uses:
    # 1. RequirementsGenerator 
    # 2. CompilationSearchEngine
    # 3. AIScriptGenerator (handles own audio generation)
    # 4. VideoStitcher (to be implemented)
    # ============================================================================

    def _generate_auto_title(self, context: str, requirements: str) -> str:
        """Generate automatic title from context and requirements."""
        # Extract key terms from context and requirements
        context_words = context.lower().replace(',', ' ').split()
        req_words = requirements.lower().replace(',', ' ').split()
        
        # Common fitness keywords to prioritize
        fitness_keywords = [
            'workout', 'exercise', 'fitness', 'training', 'routine',
            'strength', 'cardio', 'mobility', 'flexibility', 'core',
            'beginner', 'intermediate', 'advanced', 'morning', 'evening',
            'quick', 'intense', 'gentle', 'full', 'body', 'upper', 'lower'
        ]
        
        # Find relevant keywords
        key_terms = []
        for word in context_words + req_words:
            clean_word = word.strip('.,!?();')
            if clean_word in fitness_keywords and clean_word not in key_terms:
                key_terms.append(clean_word)
        
        # Create title
        if key_terms:
            title = ' '.join(key_terms[:3]).title()  # Use up to 3 key terms
            if 'routine' not in title.lower() and 'workout' not in title.lower():
                title += ' Routine'
        else:
            title = 'Custom Fitness Compilation'
        
        return title

    async def get_compilation_status(self, compilation_id: str) -> Dict[str, Any]:
        """
        Get the status of a compilation by ID.
        
        Args:
            compilation_id: Unique identifier for the compilation
            
        Returns:
            Dictionary with compilation status and metadata
        """
        try:
            # TODO: Implement with proper database operations
            # For now, return placeholder status
            return {
                "compilation_id": compilation_id,
                "status": "unknown",
                "message": "Status checking not yet implemented",
                "created_at": None,
                "completed_at": None,
                "duration": None,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get compilation status: {e}")
            return {
                "compilation_id": compilation_id,
                "status": "error",
                "message": f"Failed to retrieve status: {e}",
                "error": str(e)
            }

    async def cleanup(self):
        """Clean up pipeline resources."""
        try:
            if self.connections:
                await self.connections.cleanup()
            logger.info("✅ Pipeline cleanup completed")
        except Exception as e:
            logger.error(f"❌ Pipeline cleanup failed: {e}")

# Global pipeline instance
compilation_pipeline = CompilationPipeline()

async def get_compilation_pipeline() -> CompilationPipeline:
    """Get the global compilation pipeline instance."""
    if not compilation_pipeline.connections:
        await compilation_pipeline.initialize()
    return compilation_pipeline 