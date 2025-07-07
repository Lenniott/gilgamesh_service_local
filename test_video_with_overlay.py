#!/usr/bin/env python3
"""
Test Video Stitching with Video ID Overlay
Uses the saved compilation JSON to create the final video WITH video ID overlays.
"""

import asyncio
import json
import logging
import base64
from datetime import datetime
from typing import List, Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_video_with_overlay():
    """Test video stitching with video ID overlays."""
    
    logger.info("🎬 Testing video stitching with video ID overlays...")
    
    try:
        # Load the existing JSON file
        json_file = "test_output/compilation_full_20250707_235324.json"
        logger.info(f"📂 Loading JSON from: {json_file}")
        
        with open(json_file, 'r') as f:
            compilation_data = json.load(f)
        
        # Extract segments
        segments = compilation_data.get("segments", [])
        logger.info(f"✅ Loaded {len(segments)} segments")
        
        # Import video stitcher
        from app.video_stitcher import VideoStitcher
        from app.stitch_scenes import SceneInput
        
        # Create stitcher
        stitcher = VideoStitcher()
        
        # Convert segments to SceneInput format with video ID overlay enabled
        scene_inputs = []
        for i, segment in enumerate(segments):
            clips = segment.get("clips", [])
            if clips:
                clip = clips[0]  # Use first clip
                scene_input = SceneInput(
                    video=clip["video"],
                    video_id=clip["video_id"],
                    audio=segment.get("audio"),
                    show_debug=True  # ENABLE VIDEO ID OVERLAY
                )
                scene_inputs.append(scene_input)
                logger.info(f"  Scene {i+1}: video_id={clip['video_id'][:8]}... (show_debug=True)")
        
        logger.info(f"🔧 Creating final video with {len(scene_inputs)} scenes and video ID overlays...")
        
        # Stitch scenes together with overlays
        from app.stitch_scenes import stitch_scenes_to_base64
        final_base64 = stitch_scenes_to_base64(scene_inputs)
        
        # Save final video
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"test_output/final_video_with_overlay_{timestamp}.mp4"
        
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(final_base64))
        
        logger.info(f"✅ Final video with overlays saved to: {output_path}")
        logger.info(f"🎉 Video overlay test completed successfully!")
        
        # Get file stats
        import os
        file_size = os.path.getsize(output_path)
        logger.info(f"📊 Final video file size: {file_size / (1024*1024):.2f}MB")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_video_with_overlay()) 