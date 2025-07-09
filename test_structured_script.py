#!/usr/bin/env python3
"""
Test script for the new structured script generation approach.
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.db_connections import DatabaseConnections
from app.ai_script_generator import AIScriptGenerator
from app.compilation_search import ContentMatch

async def test_structured_script_generation():
    """Test the new structured script generation approach."""
    
    print("🧪 Testing Structured Script Generation")
    print("=" * 50)
    
    try:
        # Initialize connections
        connections = DatabaseConnections()
        await connections.connect_all()
        
        # Initialize script generator
        script_generator = AIScriptGenerator(connections)
        await script_generator.initialize()
        
        # Create mock content matches for testing
        mock_content_matches = [
            ContentMatch(
                video_id="test_video_1",
                segment_type="scene",
                start_time=0.0,
                end_time=30.0,
                relevance_score=0.8,
                content_text="Person doing squats with proper form, feet shoulder width apart",
                tags=["squat", "strength", "lower_body"],
                metadata={}
            ),
            ContentMatch(
                video_id="test_video_2", 
                segment_type="scene",
                start_time=0.0,
                end_time=25.0,
                relevance_score=0.7,
                content_text="Person performing push-ups with controlled movement",
                tags=["pushup", "strength", "upper_body"],
                metadata={}
            ),
            ContentMatch(
                video_id="test_video_3",
                segment_type="scene", 
                start_time=0.0,
                end_time=20.0,
                relevance_score=0.6,
                content_text="Person doing mobility stretches and flexibility exercises",
                tags=["mobility", "flexibility", "stretch"],
                metadata={}
            )
        ]
        
        # Test content context collection
        print("📊 Testing content context collection...")
        content_context = await script_generator.collect_content_context(mock_content_matches)
        print(f"✅ Found {len(content_context['video_segments'])} video segments")
        print(f"✅ Available exercises: {content_context['available_exercises']}")
        print(f"✅ Total duration: {content_context['total_duration']:.1f}s")
        
        # Test structured script generation
        print("\n🎬 Testing structured script generation...")
        user_requirements = "5 minutes, beginner-friendly, full body workout"
        structured_script = await script_generator.generate_structured_compilation_script(
            mock_content_matches, user_requirements
        )
        print(f"✅ Generated structured script with {len(structured_script.get('segments', []))} segments")
        print(f"✅ Workout structure: {structured_script.get('workout_structure', 'N/A')}")
        print(f"✅ Total rounds: {structured_script.get('total_rounds', 'N/A')}")
        
        # Test parsing to segments
        print("\n🔄 Testing parsing to segments...")
        segments = await script_generator.parse_structured_script_to_segments(
            structured_script, mock_content_matches
        )
        print(f"✅ Parsed into {len(segments)} segments")
        
        for i, segment in enumerate(segments):
            print(f"   Segment {i+1}: {segment['script_segment']}")
            if segment.get('clips'):
                print(f"     Clips: {len(segment['clips'])}")
        
        # Test full compilation generation (text-only mode)
        print("\n🎬 Testing full compilation generation (text-only)...")
        compilation_segments = await script_generator.generate_compilation_json(
            content_matches=mock_content_matches,
            user_requirements=user_requirements,
            include_audio=False,  # Text-only mode
            include_clips=False,  # Skip clips for testing
            aspect_ratio="9:16"
        )
        print(f"✅ Generated compilation with {len(compilation_segments)} segments")
        
        # Show final result
        print("\n📋 Final Compilation Result:")
        for i, segment in enumerate(compilation_segments):
            print(f"   {i+1}. {segment['script_segment']} ({segment['duration']:.1f}s)")
        
        print("\n✅ All tests passed! Structured script generation is working.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if 'connections' in locals():
            try:
                if hasattr(connections, 'postgres_connection') and connections.postgres_connection:
                    await connections.postgres_connection.close()
            except Exception as e:
                print(f"⚠️ Cleanup warning: {e}")

if __name__ == "__main__":
    asyncio.run(test_structured_script_generation()) 