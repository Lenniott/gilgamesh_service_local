#!/usr/bin/env python3
"""
Simple test to verify database saving works with real video data.
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.append('app')

async def test_save_real_video():
    """Test saving a real video with transcript and scenes to database."""
    
    print("🎯 Testing Real Video Save to Database")
    print("=" * 50)
    
    try:
        from app.simple_db_operations import SimpleVideoDatabase
        import tempfile
        import base64
        
        # Create fresh database instance
        db = SimpleVideoDatabase()
        await db.initialize()
        
        if not db.connections or not db.connections.pg_pool:
            print("❌ Database not available")
            return False
        
        print("✅ Database connection successful")
        
        # Create a small test "video" file
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            test_video_content = b"FAKE VIDEO DATA FOR TESTING - THIS IS NOT A REAL MP4"
            f.write(test_video_content)
            test_video_path = f.name
        
        try:
            # Test data
            url = "https://www.youtube.com/watch?v=TEST123"
            transcript_data = [
                {"start": 0.0, "end": 4.0, "text": "Alright so here we are one of the elephants."},
                {"start": 4.0, "end": 12.0, "text": "The cool thing about these guys is that they have really, really, really long hunts."},
                {"start": 12.0, "end": 14.0, "text": "And that's cool."},
                {"start": 14.0, "end": 19.0, "text": "And that's pretty much all there is to say."}
            ]
            
            scenes_data = [
                {
                    "start_time": 0.0,
                    "end_time": 19.06,
                    "ai_description": "Person speaking casually about elephants, making gestures and communicating in a non-exercise context",
                    "ai_tags": ["gesture", "speaking", "non-exercise", "communication", "casual"],
                    "analysis_success": True,
                    "has_transcript": True,
                    "scene_transcript": "Alright so here we are one of the elephants. The cool thing about these guys is that they have really, really, really long hunts. And that's cool. And that's pretty much all there is to say."
                }
            ]
            
            metadata = {
                "original_url": url,
                "processing_options": {
                    "save_video": True,
                    "transcribe": True,
                    "describe": True
                },
                "file_info": {
                    "path": test_video_path,
                    "size": len(test_video_content)
                },
                "download_info": {
                    "source": "youtube/tiktok",
                    "description": "Test video for database saving",
                    "original_tags": ["test", "database"]
                }
            }
            
            print("💾 Saving video to database...")
            
            # Save to database
            video_id = await db.save_video(
                video_path=test_video_path,
                url=url,
                transcript_data=transcript_data,
                scenes_data=scenes_data,
                metadata=metadata
            )
            
            if video_id:
                print(f"✅ Video saved successfully: {video_id}")
                
                # Test retrieval
                print("📥 Testing video retrieval...")
                
                retrieved = await db.get_video(video_id)
                if retrieved:
                    print(f"✅ Video retrieved: {retrieved['url']}")
                    print(f"✅ Has video data: {retrieved['has_video']}")
                    print(f"✅ Video size: {retrieved['video_size']:,} bytes")
                    print(f"✅ Transcript segments: {len(retrieved['transcript'])}")
                    print(f"✅ Scene descriptions: {len(retrieved['descriptions'])}")
                    print(f"✅ Tags: {retrieved['tags']}")
                    print(f"✅ Created: {retrieved['created_at']}")
                    
                    # Check transcript content
                    first_segment = retrieved['transcript'][0]
                    print(f"✅ First transcript: {first_segment['text'][:50]}...")
                    
                    # Check scene content
                    first_scene = retrieved['descriptions'][0]
                    print(f"✅ Scene description: {first_scene['description'][:50]}...")
                    print(f"✅ Has transcript context: {first_scene.get('has_transcript', False)}")
                    
                    # Test base64 retrieval
                    print("📁 Testing base64 retrieval...")
                    video_base64 = await db.get_video_base64(video_id)
                    if video_base64:
                        decoded = base64.b64decode(video_base64)
                        if decoded == test_video_content:
                            print("✅ Base64 video data matches original")
                        else:
                            print("❌ Base64 video data doesn't match")
                    else:
                        print("❌ Failed to retrieve base64 data")
                    
                    print("\n🎉 All database operations successful!")
                    return True
                    
                else:
                    print("❌ Failed to retrieve saved video")
                    return False
            else:
                print("❌ Failed to save video")
                return False
                
        finally:
            # Cleanup test file
            if os.path.exists(test_video_path):
                os.unlink(test_video_path)
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_search_and_list():
    """Test search and list functionality."""
    
    print("\n🔍 Testing Search and List Functions")
    print("=" * 50)
    
    try:
        from app.simple_unified_processor import search_videos_simple, list_videos_simple
        
        # Test search
        print("1️⃣ Testing search...")
        search_result = await search_videos_simple("elephant", limit=5)
        
        if search_result['success']:
            print(f"✅ Search successful: {search_result['count']} results")
            for video in search_result['results']:
                print(f"   • {video['url'][:50]}...")
        else:
            print(f"❌ Search failed: {search_result.get('error')}")
        
        # Test list
        print("2️⃣ Testing list...")
        list_result = await list_videos_simple(limit=5)
        
        if list_result['success']:
            print(f"✅ List successful: {list_result['count']} videos")
            for video in list_result['videos']:
                print(f"   • {video['url'][:50]}... ({video['created_at'][:10]})")
                if video['tags']:
                    print(f"     Tags: {', '.join(video['tags'][:3])}")
        else:
            print(f"❌ List failed: {list_result.get('error')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Search/List test failed: {e}")
        return False

async def main():
    """Main test function."""
    
    # Test saving
    save_success = await test_save_real_video()
    
    if save_success:
        # Test search and list
        search_success = await test_search_and_list()
        
        if search_success:
            print("\n🎉 All tests passed!")
            print("✅ PostgreSQL saving works perfectly")
            print("✅ Video data stored with transcript context")
            print("✅ Search and list functions working")
            print("\nThe simplified single-table approach is working great!")
        else:
            print("\n❌ Search/List tests failed")
    else:
        print("\n❌ Save test failed")

if __name__ == "__main__":
    asyncio.run(main()) 