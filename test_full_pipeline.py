#!/usr/bin/env python3
"""
Test script for the full pipeline with structured script generation.
"""

import asyncio
import sys
import os
import json

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.video_compilation_pipeline import CompilationPipeline, CompilationRequest

async def test_full_pipeline():
    """Test the full compilation pipeline with structured script generation."""
    
    print("🧪 Testing Full Pipeline with Structured Script Generation")
    print("=" * 60)
    
    try:
        # Initialize pipeline
        pipeline = CompilationPipeline()
        await pipeline.initialize()
        
        # Create test request
        request = CompilationRequest(
            context="I'm creating a morning workout routine",
            requirements="5 minutes, beginner-friendly, full body workout with squats and push-ups",
            title="Morning Full Body Workout",
            voice_preference="alloy",
            aspect_ratio="9:16",
            max_duration=300.0,  # 5 minutes
            include_base64=False,  # Skip final video for testing
            audio=False,  # Text-only mode for cost reduction
            clips=False,  # Skip clips for testing
            text_only=True,  # Enable text-only mode
            max_segments_per_video=2,  # Diversity control
            min_unique_videos=3  # Diversity control
        )
        
        print("📋 Test Request:")
        print(f"   Context: {request.context}")
        print(f"   Requirements: {request.requirements}")
        print(f"   Text-only mode: {request.text_only}")
        print(f"   Max segments per video: {request.max_segments_per_video}")
        print(f"   Min unique videos: {request.min_unique_videos}")
        
        # Process compilation request
        print("\n🎬 Processing compilation request...")
        response = await pipeline.process_compilation_request(request)
        
        if response.success:
            print(f"✅ Compilation successful!")
            print(f"   Generated video ID: {response.generated_video_id}")
            print(f"   Duration: {response.duration:.1f}s")
            print(f"   Source videos used: {response.source_videos_used}")
            print(f"   Processing time: {response.processing_time:.1f}s")
            
            if response.compilation_json:
                segments = response.compilation_json.get("segments", [])
                print(f"\n📋 Generated {len(segments)} segments:")
                
                # Track diversity
                video_ids = set()
                for i, segment in enumerate(segments):
                    script = segment.get("script_segment", "No script")
                    duration = segment.get("duration", 0)
                    clips = segment.get("clips", [])
                    
                    print(f"   {i+1}. {script} ({duration:.1f}s)")
                    
                    # Track video diversity
                    for clip in clips:
                        video_id = clip.get("video_id")
                        if video_id:
                            video_ids.add(video_id)
                
                print(f"\n🎯 Diversity Analysis:")
                print(f"   Unique videos used: {len(video_ids)}")
                print(f"   Target minimum: {request.min_unique_videos}")
                print(f"   Diversity achieved: {'✅' if len(video_ids) >= request.min_unique_videos else '❌'}")
                
                # Show video IDs for verification
                if video_ids:
                    print(f"   Video IDs: {list(video_ids)}")
            
        else:
            print(f"❌ Compilation failed: {response.error}")
        
        print("\n✅ Full pipeline test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if 'pipeline' in locals():
            await pipeline.cleanup()

if __name__ == "__main__":
    asyncio.run(test_full_pipeline()) 