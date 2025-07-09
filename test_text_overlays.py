#!/usr/bin/env python3
"""
Test Text Overlays in Video Stitching Pipeline
Tests that text overlays are properly passed through the video stitching pipeline.
"""

import asyncio
import logging
import json
from app.db_connections import DatabaseConnections
from app.ai_script_generator import AIScriptGenerator
from app.video_compilation_pipeline import CompilationPipeline, CompilationRequest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_text_overlays():
    """Test that text overlays are properly included in the video stitching pipeline."""
    logger.info("🧪 Testing Text Overlays in Video Stitching Pipeline")
    logger.info("=" * 60)
    
    try:
        # Initialize connections
        connections = DatabaseConnections()
        await connections.connect_all()
        
        # Initialize script generator
        script_generator = AIScriptGenerator(connections)
        await script_generator.initialize()
        
        # Create a simple test compilation
        test_context = "I want to test text overlays"
        test_requirements = "5 minutes, simple exercises with clear text on screen"
        
        # Create compilation request
        request = CompilationRequest(
            context=test_context,
            requirements=test_requirements,
            title="Text Overlay Test",
            voice_preference="alloy",
            max_duration=300.0,  # 5 minutes
            include_base64=False,  # Don't include video data for testing
            text_only=True,  # Text-only mode
            show_debug_overlay=True  # Show video IDs for debugging
        )
        
        # Initialize pipeline
        pipeline = CompilationPipeline()
        await pipeline.initialize()
        
        logger.info("🎬 Processing compilation request...")
        response = await pipeline.process_compilation_request(request)
        
        if response.success:
            logger.info("✅ Compilation generated successfully!")
            logger.info(f"📊 Duration: {response.duration:.1f}s")
            logger.info(f"🎬 Source Videos: {response.source_videos_used}")
            
            # Check if compilation JSON has text overlays
            if response.compilation_json:
                segments = response.compilation_json.get("segments", [])
                logger.info(f"📝 Found {len(segments)} segments")
                
                text_overlay_count = 0
                for i, segment in enumerate(segments, 1):
                    text_overlay = segment.get("text_overlay")
                    if text_overlay:
                        text_overlay_count += 1
                        logger.info(f"   Segment {i}: '{text_overlay}'")
                    else:
                        logger.info(f"   Segment {i}: No text overlay")
                
                logger.info(f"📊 Text overlays found: {text_overlay_count}/{len(segments)}")
                
                if text_overlay_count > 0:
                    logger.info("✅ Text overlays are being generated!")
                else:
                    logger.warning("⚠️ No text overlays found in segments")
            else:
                logger.warning("⚠️ No compilation JSON in response")
        else:
            logger.error(f"❌ Compilation failed: {response.error}")
        
        # Clean up
        await connections.close_all()
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_text_overlays()) 