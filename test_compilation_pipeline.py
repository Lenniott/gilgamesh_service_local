#!/usr/bin/env python3
"""
Test AI Video Compilation Pipeline
Tests the new simplified JSON-driven architecture
"""

import asyncio
import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, List
import base64 # Added for base64 decoding

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_compilation_json(compilation_json: List[Dict[str, Any]]) -> bool:
    """Validate compilation JSON matches our vision doc format."""
    try:
        if not isinstance(compilation_json, list):
            logger.error("❌ Compilation JSON must be a list")
            return False
            
        for segment in compilation_json:
            # Check required fields - matching the working JSON structure
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
                
        return True
            except Exception as e:
        logger.error(f"❌ JSON validation failed: {e}")
        return False

async def test_compilation_pipeline():
    """Test the complete AI video compilation pipeline."""
    
    logger.info("🧪 Testing AI Video Compilation Pipeline...")
    
    try:
        # Import the pipeline
        from app.video_compilation_pipeline import CompilationPipeline, CompilationRequest, CompilationResponse
        
        # Create pipeline instance
        pipeline = CompilationPipeline()
        await pipeline.initialize()
        
        # Test compilation request
        test_request = CompilationRequest(
            context="morning 10 minute workout, full body mobility and strength for beginners, but i also want to work being able to do a handstand so throw in some beginner exercises for that too, and some beginner yoga poses progression for pull ups",
            requirements="30 seconds, show exercises, bodyweight only",
            title="Test JSON Generation",
            voice_preference="alloy",
            aspect_ratio="square",  # Using new aspect_ratio parameter
            max_duration=30.0,
            audio=True,  # Include audio in JSON
            clips=True,  # Include clips in JSON
            include_base64=True,  # Include final video
            show_debug_overlay=True  # Show video IDs for debugging
        )
        
        logger.info("📋 Test Request:")
        logger.info(f"  Context: {test_request.context}")
        logger.info(f"  Requirements: {test_request.requirements}")
        logger.info(f"  Duration: {test_request.max_duration}s")
        logger.info(f"  Aspect Ratio: {test_request.aspect_ratio}")
        
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
                    else:
                        logger.warning("⚠️ No final video in response")
                else:
                    logger.error("❌ Invalid compilation JSON format")
                    return False
            
            if result.metadata:
                logger.info("📈 Metadata:")
                for key, value in result.metadata.items():
                    logger.info(f"  {key}: {value}")
            
            return True
        else:
            logger.error("❌ COMPILATION FAILED!")
            logger.error(f"Error: {result.error}")
            return False
            
    except Exception as e:
        logger.error(f"❌ TEST FAILED: {e}")
        return False

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

async def run_all_tests():
    """Run all tests in sequence."""
    
    logger.info("🧪 STARTING AI VIDEO COMPILATION PIPELINE TESTS")
    logger.info("=" * 60)
    
    # Test 1: Database requirements
    logger.info("\n🔍 TEST 1: Database Requirements")
    db_test = await test_database_requirements()
    
    # Test 2: Full pipeline
    logger.info("\n🚀 TEST 2: Full Pipeline")
    pipeline_test = await test_compilation_pipeline()
    
    # Summary
    logger.info("\n📊 TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Database Test: {'✅' if db_test else '❌'}")
    logger.info(f"Pipeline Test: {'✅' if pipeline_test else '❌'}")
    
    return all([db_test, pipeline_test])

if __name__ == "__main__":
    asyncio.run(run_all_tests()) 