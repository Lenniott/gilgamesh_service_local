#!/usr/bin/env python3
"""
Test script for complete scene detection + AI analysis pipeline.
Tests with YouTube video: https://www.youtube.com/shorts/2hvRmabCWS4
"""

import os
import sys
import asyncio
import tempfile
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add app to path
sys.path.append(os.path.dirname(__file__))

from app.scene_detection import extract_scenes_with_ai_analysis
from app.downloaders import download_youtube

async def test_complete_ai_pipeline():
    """Test the complete scene detection + AI analysis pipeline."""
    
    # Test video URL
    test_url = "https://www.youtube.com/shorts/2hvRmabCWS4"
    
    print("🧠 COMPLETE AI SCENE ANALYSIS TEST")
    print("=" * 60)
    print(f"🔗 Video URL: {test_url}")
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  WARNING: OPENAI_API_KEY not found in environment!")
        print("Set your OpenAI API key to enable GPT-4 Vision analysis:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        print("\nRunning without AI analysis...")
        use_ai = False
    else:
        print("✅ OpenAI API key found - AI analysis enabled")
        use_ai = True
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Working directory: {temp_dir}")
        
        try:
            # Step 1: Download the video
            print("\n📥 Downloading video...")
            result = await download_youtube(test_url, temp_dir)
            
            video_files = [f for f in result['files'] if f.lower().endswith(('.mp4', '.mkv', '.webm'))]
            
            if not video_files:
                print("❌ No video files found!")
                return
            
            video_path = video_files[0]
            print(f"✅ Downloaded: {os.path.basename(video_path)}")
            print(f"📝 Description: {result.get('description', 'N/A')[:100]}...")
            
            # Step 2: Create frames output directory
            frames_dir = os.path.join(temp_dir, "ai_analysis_frames")
            
            # Step 3: Run complete scene analysis with AI
            print(f"\n🤖 Running complete scene analysis with AI...")
            print("-" * 50)
            
            analyzed_scenes = await extract_scenes_with_ai_analysis(
                video_path, 
                frames_dir, 
                threshold=0.22,
                use_ai_analysis=use_ai
            )
            
            # Step 4: Display results
            print(f"\n📊 COMPLETE ANALYSIS RESULTS")
            print("=" * 60)
            print(f"🎬 Total scenes analyzed: {len(analyzed_scenes)}")
            
            for i, scene in enumerate(analyzed_scenes):
                print(f"\n🎞️  SCENE {i+1}:")
                print(f"   ⏱️  Time: {scene['start_time']:.2f}s - {scene['end_time']:.2f}s ({scene['end_time'] - scene['start_time']:.2f}s)")
                print(f"   🤖 AI Success: {'✅' if scene['analysis_success'] else '❌'}")
                print(f"   📖 Description: {scene['ai_description']}")
                print(f"   🏷️  Tags: {', '.join(scene['ai_tags'])}")
            
            # Step 5: Create structured JSON output
            output_data = {
                "video_url": test_url,
                "total_scenes": len(analyzed_scenes),
                "analysis_timestamp": asyncio.get_event_loop().time(),
                "ai_analysis_enabled": use_ai,
                "scenes": analyzed_scenes
            }
            
            # Save results to file
            output_file = os.path.join(os.getcwd(), "ai_scene_analysis_results.json")
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            print(f"\n💾 RESULTS SAVED TO: {output_file}")
            
            # Step 6: Verify cleanup
            print(f"\n🧹 CLEANUP VERIFICATION:")
            if os.path.exists(frames_dir):
                remaining_files = os.listdir(frames_dir)
                if remaining_files:
                    print(f"⚠️  {len(remaining_files)} files still remain in frames directory")
                else:
                    print("✅ All frame files successfully cleaned up")
            else:
                print("✅ Frames directory completely removed")
            
            print(f"\n🎯 FINAL STRUCTURE EXAMPLE:")
            print("=" * 40)
            if analyzed_scenes:
                example_scene = analyzed_scenes[0]
                print("Scene structure:")
                for key, value in example_scene.items():
                    if isinstance(value, list):
                        print(f"  {key}: {value}")
                    else:
                        print(f"  {key}: {value}")
            
            print(f"\n✅ Complete AI scene analysis test finished!")
            print(f"📄 Check the JSON file for full results: {output_file}")
            
        except Exception as e:
            print(f"❌ Error during test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_complete_ai_pipeline()) 