#!/usr/bin/env python3
"""
Test Video Stitching with Existing JSON
Uses the saved compilation JSON to create the final video without spending more credits.
"""

import asyncio
import json
import logging
import base64
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_video_stitching():
    """Test video stitching using existing JSON file."""
    
    logger.info("🎬 Testing video stitching with existing JSON...")
    
    try:
        # Load the existing JSON file
        json_file = "test_output/compilation_full_20250707_235324.json"
        logger.info(f"📂 Loading JSON from: {json_file}")
        
        with open(json_file, 'r') as f:
            compilation_json = json.load(f)
        
        logger.info(f"✅ Loaded JSON with {len(compilation_json.get('segments', []))} segments")
        
        # Import the video stitcher
        from app.video_stitcher import VideoStitcher, StitchingSettings
        
        # Create stitcher and settings
        stitcher = VideoStitcher()
        settings = StitchingSettings(
            aspect_ratio="square",  # Match the test request
            framerate=30,
            loop_clips=True
        )
        
        logger.info("🔧 Creating final video...")
        
        # Stitch the video
        result = await stitcher.stitch_compilation_video(compilation_json, settings)
        
        logger.info(f"✅ Video stitching successful!")
        logger.info(f"📊 Video Details:")
        logger.info(f"  Duration: {result.duration:.2f}s")
        logger.info(f"  File Size: {result.file_size / 1024 / 1024:.2f}MB")
        logger.info(f"  Segments Processed: {result.segments_processed}")
        logger.info(f"  Aspect Ratio: {result.aspect_ratio}")
        
        # Save the final video
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_path = f"test_output/final_video_{timestamp}.mp4"
        
        with open(video_path, "wb") as f:
            f.write(base64.b64decode(result.video_base64))
        
        logger.info(f"✅ Final video saved to: {video_path}")
        logger.info("🎉 Video stitching test completed successfully!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Video stitching test failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_video_stitching()) 