#!/usr/bin/env python3
"""
Test script for enhanced scene detection with extreme frame analysis.
Tests with YouTube video: https://www.youtube.com/shorts/2hvRmabCWS4
"""

import os
import sys
import asyncio
import tempfile
import shutil
from pathlib import Path

# Add app to path
sys.path.append(os.path.dirname(__file__))

from app.scene_detection import extract_scene_cuts_and_extreme_frames
from app.downloaders import download_youtube

async def test_enhanced_scene_detection():
    """Test the enhanced scene detection on the mobility exercises video."""
    
    # Test video URL
    test_url = "https://www.youtube.com/shorts/2hvRmabCWS4"
    
    print("🎯 Enhanced Scene Detection Test")
    print("=" * 50)
    print(f"🔗 Video URL: {test_url}")
    
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
            print(f"🏷️  Tags: {result.get('tags', [])}")
            
            # Step 2: Create frames output directory
            frames_dir = os.path.join(temp_dir, "extreme_frames")
            os.makedirs(frames_dir, exist_ok=True)
            
            # Step 3: Run enhanced scene detection
            print(f"\n🔍 Running enhanced scene detection...")
            print("-" * 40)
            
            scenes = extract_scene_cuts_and_extreme_frames(
                video_path, 
                frames_dir, 
                threshold=0.22  # Standard threshold
            )
            
            # Step 4: Display results
            print(f"\n📊 RESULTS SUMMARY")
            print("=" * 50)
            print(f"🎬 Total scenes found: {len(scenes)}")
            
            total_extreme_frames = 0
            for i, scene in enumerate(scenes):
                print(f"\n🎞️  SCENE {i+1}:")
                print(f"   ⏱️  Duration: {scene['start_time']:.2f}s - {scene['end_time']:.2f}s ({scene['end_time'] - scene['start_time']:.2f}s)")
                print(f"   🎯 Extreme frames: {len(scene['extreme_frames'])}")
                
                for j, frame in enumerate(scene['extreme_frames']):
                    print(f"      {j+1}. {frame['frame_type'].upper()}: {frame['timestamp']:.2f}s")
                    print(f"         📁 {os.path.basename(frame['frame_path'])}")
                    print(f"         📈 Difference: {frame['difference_score']:.3f}")
                
                total_extreme_frames += len(scene['extreme_frames'])
            
            print(f"\n🎯 TOTAL EXTREME FRAMES: {total_extreme_frames}")
            
            # Step 5: List all extracted frame files
            print(f"\n📸 EXTRACTED FRAME FILES:")
            print("-" * 40)
            
            frame_files = []
            for root, dirs, files in os.walk(frames_dir):
                for file in files:
                    if file.endswith('.jpg'):
                        frame_path = os.path.join(root, file)
                        frame_files.append(frame_path)
            
            frame_files.sort()
            
            if frame_files:
                print(f"📁 Found {len(frame_files)} frame files in: {frames_dir}")
                for frame_file in frame_files:
                    rel_path = os.path.relpath(frame_file, frames_dir)
                    file_size = os.path.getsize(frame_file) / 1024  # KB
                    print(f"   • {rel_path} ({file_size:.1f} KB)")
                
                # Copy frames to a permanent location for inspection
                output_dir = os.path.join(os.getcwd(), "test_extreme_frames_output")
                if os.path.exists(output_dir):
                    shutil.rmtree(output_dir)
                shutil.copytree(frames_dir, output_dir)
                
                print(f"\n📋 FRAMES COPIED TO: {output_dir}")
                print("🔍 You can now inspect the extreme frames!")
                
                # Create a summary file
                summary_file = os.path.join(output_dir, "ANALYSIS_SUMMARY.txt")
                with open(summary_file, 'w') as f:
                    f.write("ENHANCED SCENE DETECTION ANALYSIS\n")
                    f.write("=" * 50 + "\n")
                    f.write(f"Video URL: {test_url}\n")
                    f.write(f"Total scenes: {len(scenes)}\n")
                    f.write(f"Total extreme frames: {total_extreme_frames}\n\n")
                    
                    for i, scene in enumerate(scenes):
                        f.write(f"SCENE {i+1}: {scene['start_time']:.2f}s - {scene['end_time']:.2f}s\n")
                        for frame in scene['extreme_frames']:
                            f.write(f"  {frame['frame_type']}: {frame['timestamp']:.2f}s ")
                            f.write(f"(diff: {frame['difference_score']:.3f}) ")
                            f.write(f"-> {os.path.basename(frame['frame_path'])}\n")
                        f.write("\n")
                
                print(f"📄 Analysis summary: {summary_file}")
                
            else:
                print("❌ No frame files found!")
            
            print(f"\n✅ Enhanced scene detection test completed!")
            
        except Exception as e:
            print(f"❌ Error during test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_enhanced_scene_detection()) 