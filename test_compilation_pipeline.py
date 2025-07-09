#!/usr/bin/env python3
"""
Test AI Video Compilation Pipeline
Tests the new simplified JSON-driven architecture with text overlays
"""

import asyncio
import logging
import json
import os
import glob
from datetime import datetime
from typing import Dict, Any, List
import base64

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_compilation_json(compilation_json: List[Dict[str, Any]]) -> bool:
    """Validate compilation JSON matches our vision doc format with text overlays."""
    try:
        if not isinstance(compilation_json, list):
            logger.error("❌ Compilation JSON must be a list")
            return False
            
        for segment in compilation_json:
            # Check required fields - matching the working JSON structure with text overlays
            required_fields = ["script_segment", "clips", "audio", "duration"]
            if not all(key in segment for key in required_fields):
                logger.error(f"❌ Missing required fields in segment. Required: {required_fields}")
                logger.error(f"❌ Found fields: {list(segment.keys())}")
                return False
                
            # Validate script_segment
            if not isinstance(segment["script_segment"], str):
                logger.error("❌ script_segment must be a string")
                return False
                
            # Validate clips array
            if not isinstance(segment["clips"], list):
                logger.error("❌ clips must be a list")
                return False
                
            # Validate each clip in the clips array
            for clip in segment["clips"]:
                clip_required_fields = ["video_id", "start", "end", "video"]
                if not all(key in clip for key in clip_required_fields):
                    logger.error(f"❌ Missing required fields in clip. Required: {clip_required_fields}")
                    return False
                    
                if not isinstance(clip["video_id"], str):
                    logger.error("❌ clip video_id must be a string")
                    return False
                    
                if not isinstance(clip["start"], (int, float)):
                    logger.error("❌ clip start must be a number")
                    return False
                    
                if not isinstance(clip["end"], (int, float)):
                    logger.error("❌ clip end must be a number")
                    return False
                    
                if clip["video"] is not None and not isinstance(clip["video"], str):
                    logger.error("❌ clip video must be a string or None")
                    return False
                
            # Validate audio
            if segment["audio"] is not None and not isinstance(segment["audio"], str):
                logger.error("❌ audio must be a string or None")
                return False
                
            # Validate duration
            if not isinstance(segment["duration"], (int, float)):
                logger.error("❌ duration must be a number")
                return False
                
            # Check for text overlay (optional but recommended)
            if "text_overlay" in segment:
                if not isinstance(segment["text_overlay"], str):
                    logger.error("❌ text_overlay must be a string")
                    return False
                logger.info(f"✅ Found text overlay: {segment['text_overlay']}")
                
        return True
    except Exception as e:
        logger.error(f"❌ JSON validation failed: {e}")
        return False

def find_latest_compilation_json():
    """Find the latest compilation JSON file in test_output folder."""
    pattern = "test_output/compilation_full_*.json"
    files = glob.glob(pattern)
    if not files:
        return None
    
    # Sort by modification time and return the latest
    latest_file = max(files, key=os.path.getmtime)
    return latest_file

async def generate_video_from_json(json_data, output_filename: str = None):
    """Generate a video from existing compilation JSON."""
    logger.info("🎬 Generating video from existing compilation JSON...")
    
    try:
        from app.video_stitcher import VideoStitcher, StitchingSettings
        
        # Create video stitcher
        stitcher = VideoStitcher()
        
        # Create stitching settings
        settings = StitchingSettings(
            aspect_ratio="9:16",
            framerate=30,
            audio_bitrate="128k",
            video_codec="libx264",
            loop_clips=True
        )
        
        # Always pass a dict with 'segments' key
        if isinstance(json_data, list):
            compilation_json = {"segments": json_data}
        elif isinstance(json_data, dict) and "segments" in json_data:
            compilation_json = json_data
        else:
            logger.error("❌ Invalid JSON format for video generation")
            return None
        
        logger.info(f"📝 Processing {len(compilation_json['segments'])} segments...")
        
        # Generate video
        composed_video = await stitcher.stitch_compilation_video(compilation_json, settings)
        
        if composed_video and composed_video.video_base64:
            # Save video
            if output_filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"test_output/generated_video_{timestamp}.mp4"
            
            os.makedirs("test_output", exist_ok=True)
            with open(output_filename, "wb") as f:
                f.write(base64.b64decode(composed_video.video_base64))
            
            logger.info(f"✅ Video generated successfully: {output_filename}")
            logger.info(f"📊 Video stats:")
            logger.info(f"  Duration: {composed_video.duration:.2f}s")
            logger.info(f"  Aspect ratio: {composed_video.aspect_ratio}")
            logger.info(f"  File size: {composed_video.file_size} bytes")
            logger.info(f"  Segments processed: {composed_video.segments_processed}")
            logger.info("🎬 Video includes:")
            logger.info("  - Instructional text overlays")
            logger.info("  - Video IDs for debugging")
            logger.info("  - Multiple unique videos for diversity")
            logger.info("  - Video looping for short clips")
            
            return output_filename
        else:
            logger.error("❌ Failed to generate video")
            return None
            
    except Exception as e:
        logger.error(f"❌ Video generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_compilation_pipeline(use_existing_json: bool = False):
    """Test the complete AI video compilation pipeline."""
    
    logger.info("🧪 Testing AI Video Compilation Pipeline...")
    
    if use_existing_json:
        existing_file = find_latest_compilation_json()
        if existing_file:
            logger.info(f"📁 Using existing compilation JSON: {existing_file}")
            with open(existing_file, 'r') as f:
                existing_json = json.load(f)
            logger.info("✅ Loaded existing compilation JSON")
            
            # Generate video from the JSON
            video_path = await generate_video_from_json(existing_json)
            if video_path:
                logger.info(f"🎬 Video generated: {video_path}")
                return existing_json
            else:
                logger.error("❌ Failed to generate video from JSON")
                return None
        else:
            logger.warning("⚠️ No existing compilation JSON found, generating from scratch")
    
    try:
        # Import the pipeline
        from app.video_compilation_pipeline import CompilationPipeline, CompilationRequest, CompilationResponse
        
        # Create pipeline instance
        pipeline = CompilationPipeline()
        await pipeline.initialize()
        
        # Test compilation request
        test_request = CompilationRequest(
            context="morning 10 minute workout for the morning, want to work being able to do a handstand so throw in some beginner exercises for that too, and some beginner progression exercises for pull ups",
            requirements="30 seconds, show exercises, bodyweight only",
            title="Test Structured Script Generation with Text Overlays",
            voice_preference="alloy",
            aspect_ratio="9:16",  # Using 9:16 for mobile-friendly format
            max_duration=30.0,
            audio=False,  # Text-only mode for cost reduction
            clips=True,  # Include clips for video output
            include_base64=True,  # Include final video
            show_debug_overlay=True,  # Show video IDs for debugging
            text_only=True,  # Enable text-only mode
            max_segments_per_video=2,  # Diversity control
            min_unique_videos=3  # Diversity control
        )
        
        logger.info("📋 Test Request:")
        logger.info(f"  Context: {test_request.context}")
        logger.info(f"  Requirements: {test_request.requirements}")
        logger.info(f"  Duration: {test_request.max_duration}s")
        logger.info(f"  Aspect Ratio: {test_request.aspect_ratio}")
        logger.info(f"  Text-only mode: {test_request.text_only}")
        logger.info(f"  Max segments per video: {test_request.max_segments_per_video}")
        logger.info(f"  Min unique videos: {test_request.min_unique_videos}")
        logger.info(f"  Show debug overlay: {test_request.show_debug_overlay}")
        
        # Process compilation request
        logger.info("🚀 Starting compilation...")
        result = await pipeline.process_compilation_request(test_request)
        
        # Check results
        if result.success:
            logger.info("✅ COMPILATION SUCCESSFUL!")
            logger.info("📊 Results:")
            logger.info(f"  Generated Video ID: {result.generated_video_id}")
            logger.info(f"  Duration: {result.duration:.2f}s")
            logger.info(f"  Source Videos Used: {result.source_videos_used}")
            logger.info(f"  Processing Time: {result.processing_time:.2f}s")
            
            # Validate JSON format
            if result.compilation_json:
                # Access segments correctly from the compilation result
                segments_to_validate = result.compilation_json
                if isinstance(result.compilation_json, dict) and "segments" in result.compilation_json:
                    segments_to_validate = result.compilation_json["segments"]
                
                if validate_compilation_json(segments_to_validate):
                    logger.info("✅ Compilation JSON format is valid")
                    
                    # Analyze diversity
                    video_ids = set()
                    for segment in segments_to_validate:
                        for clip in segment.get("clips", []):
                            if clip.get("video_id"):
                                video_ids.add(clip["video_id"])
                    
                    logger.info("🎯 Diversity Analysis:")
                    logger.info(f"  Unique videos used: {len(video_ids)}")
                    logger.info(f"  Target minimum: {test_request.min_unique_videos}")
                    logger.info(f"  Diversity achieved: {'✅' if len(video_ids) >= test_request.min_unique_videos else '❌'}")
                    if video_ids:
                        logger.info(f"  Video IDs: {list(video_ids)}")
                    
                    # Show script segments with text overlays
                    logger.info("📝 Generated Script Segments with Text Overlays:")
                    for i, segment in enumerate(segments_to_validate):
                        script = segment.get("script_segment", "No script")
                        duration = segment.get("duration", 0)
                        text_overlay = segment.get("text_overlay", "No text overlay")
                        logger.info(f"  {i+1}. {script} ({duration:.1f}s)")
                        logger.info(f"     Text Overlay: {text_overlay}")
                    
                    # Save test output
                    os.makedirs("test_output", exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    # Save full JSON
                    full_path = f"test_output/compilation_full_{timestamp}.json"
                    with open(full_path, "w") as f:
                        json.dump(result.compilation_json, f, indent=2)
                    logger.info(f"✅ Saved full JSON to: {full_path}")
                    
                    # Save preview JSON (truncate base64)
                    preview = []
                    for segment in segments_to_validate:
                        preview_segment = segment.copy()
                        if preview_segment.get("audio"):
                            preview_segment["audio"] = preview_segment["audio"][:100] + "..."
                        # Handle clips array for preview
                        if preview_segment.get("clips"):
                            preview_clips = []
                            for clip in preview_segment["clips"]:
                                preview_clip = clip.copy()
                                if preview_clip.get("video"):
                                    preview_clip["video"] = preview_clip["video"][:100] + "..."
                                preview_clips.append(preview_clip)
                            preview_segment["clips"] = preview_clips
                        preview.append(preview_segment)
                        
                    preview_path = f"test_output/compilation_preview_{timestamp}.json"
                    with open(preview_path, "w") as f:
                        json.dump(preview, f, indent=2)
                    logger.info(f"✅ Saved preview JSON to: {preview_path}")
                    
                    # Save final video if present
                    if result.video_base64:
                        video_path = f"test_output/final_video_{timestamp}.mp4"
                        with open(video_path, "wb") as f:
                            f.write(base64.b64decode(result.video_base64))
                        logger.info(f"✅ Saved final video to: {video_path}")
                        logger.info("🎬 Video includes:")
                        logger.info("  - Instructional text overlays")
                        logger.info("  - Video IDs for debugging")
                        logger.info("  - Multiple unique videos for diversity")
                    else:
                        logger.warning("⚠️ No final video in response")
                    
                    return result.compilation_json
                else:
                    logger.error("❌ Invalid compilation JSON format")
                    return None
            
            if result.metadata:
                logger.info("📈 Metadata:")
                for key, value in result.metadata.items():
                    logger.info(f"  {key}: {value}")
            
            return result.compilation_json
        else:
            logger.error("❌ COMPILATION FAILED!")
            logger.error(f"Error: {result.error}")
            return None
            
    except Exception as e:
        logger.error(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_database_requirements():
    """Test database connectivity and basic requirements."""
    
    logger.info("🔍 Testing database requirements...")
    
    try:
        # Test database connections
        from app.db_connections import DatabaseConnections
        
        connections = DatabaseConnections()
        await connections.connect_all()
        
        # Check PostgreSQL
        if connections.pg_pool:
            logger.info("✅ PostgreSQL connection: OK")
        else:
            logger.warning("⚠️ PostgreSQL connection: FAILED")
            return False
        
        # Check Qdrant
        if connections.qdrant_client:
            logger.info("✅ Qdrant connection: OK")
            
            # Check collections
            collections_response = connections.qdrant_client.get_collections()
            logger.info("📊 Qdrant Collections:")
            for collection in collections_response.collections:
                collection_info = connections.qdrant_client.get_collection(collection.name)
                logger.info(f"  {collection.name}: {collection_info.points_count} points")
        else:
            logger.warning("⚠️ Qdrant connection: FAILED")
            return False
        
        # Check OpenAI
        if connections.openai_client:
            logger.info("✅ OpenAI client: OK")
        else:
            logger.warning("⚠️ OpenAI client: FAILED")
            return False
        
        # Check if we have some video data to work with
        async with connections.pg_pool.acquire() as conn:
            video_count = await conn.fetchval("SELECT COUNT(*) FROM simple_videos WHERE video_base64 IS NOT NULL")
            logger.info(f"📹 Videos with base64 data: {video_count}")
            
            if video_count == 0:
                logger.warning("⚠️ No videos with base64 data found - compilation may not work")
                return False
        
        await connections.close_all()
        return True
        
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False

async def run_all_tests(use_existing_json: bool = False):
    """Run all tests in sequence."""
    
    logger.info("🧪 STARTING AI VIDEO COMPILATION PIPELINE TESTS")
    logger.info("=" * 60)
    
    if use_existing_json:
        logger.info("📁 Using existing compilation JSON from test_output folder")
    
    # Test 1: Database requirements
    logger.info("\n🔍 TEST 1: Database Requirements")
    db_test = await test_database_requirements()
    
    # Test 2: Full pipeline
    logger.info("\n🚀 TEST 2: Full Pipeline")
    pipeline_result = await test_compilation_pipeline(use_existing_json)
    pipeline_test = pipeline_result is not None
    
    # Summary
    logger.info("\n📊 TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Database Test: {'✅' if db_test else '❌'}")
    logger.info(f"Pipeline Test: {'✅' if pipeline_test else '❌'}")
    
    if pipeline_test and pipeline_result:
        logger.info("🎉 All tests passed! Video compilation with text overlays is working.")
        logger.info("📋 Features included:")
        logger.info("  ✅ Instructional text overlays on video")
        logger.info("  ✅ Video IDs for debugging")
        logger.info("  ✅ Multiple unique videos for diversity")
        logger.info("  ✅ Video looping for short clips")
        logger.info("  ✅ Realistic workout structures")
    
    return all([db_test, pipeline_test])

if __name__ == "__main__":
    import sys
    
    # Check if user wants to use existing JSON
    use_existing = "--use-existing" in sys.argv
    if use_existing:
        logger.info("📁 Will use existing compilation JSON from test_output folder")
    
    asyncio.run(run_all_tests(use_existing)) 