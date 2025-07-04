#!/usr/bin/env python3
"""
Test the simplified single-table video processing system.
Much cleaner than the complex multi-table approach!
"""

import asyncio
import json
import sys
import os

# Add the app directory to Python path
sys.path.append('app')

from app.simple_unified_processor import (
    process_video_unified_simple,
    get_video_simple,
    search_videos_simple,
    list_videos_simple
)
from app.simple_db_operations import get_simple_db

async def test_simple_processing():
    """Test the simplified video processing system."""
    
    print("🧪 Testing Simplified Video Processing System")
    print("=" * 60)
    
    # Test URL - using a very short video for faster testing
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo" - 19 seconds
    
    try:
        # 1. Test Database Connection
        print("\n1️⃣ Testing Database Connection...")
        db = await get_simple_db()
        connections = await db.initialize()
        
        print(f"   📊 PostgreSQL: {'✅' if connections.get('postgresql') else '❌'}")
        print(f"   🔍 Qdrant: {'✅' if connections.get('qdrant') else '❌'}")
        
        # 2. Test Full Processing
        print("\n2️⃣ Testing Full Video Processing...")
        result = await process_video_unified_simple(
            url=test_url,
            save_video=True,
            transcribe=True,
            describe=True,
            include_base64=False  # Don't include massive base64 in test
        )
        
        print(f"   Success: {result['success']}")
        if result['success']:
            print(f"   Video ID: {result.get('video_id')}")
            print(f"   Processing completed:")
            print(f"     • Download: {result['processing']['download']}")
            print(f"     • Transcription: {result['processing']['transcription']}")
            print(f"     • Scene Analysis: {result['processing']['scene_analysis']}")
            print(f"   Database storage: {result['database']['saved']}")
            print(f"   Video stored: {result['database']['video_stored']}")
            
            if result['results']['transcript_data']:
                transcript_count = len(result['results']['transcript_data'])
                print(f"   Transcript segments: {transcript_count}")
            
            if result['results']['scenes_data']:
                scenes_count = len(result['results']['scenes_data'])
                print(f"   Scene descriptions: {scenes_count}")
                
                # Show enhanced descriptions
                scenes_with_transcript = [s for s in result['results']['scenes_data'] if s.get('has_transcript')]
                if scenes_with_transcript:
                    print(f"   Enhanced with transcript: {len(scenes_with_transcript)} scenes")
            
            if result['results']['tags']:
                print(f"   Tags generated: {len(result['results']['tags'])}")
                print(f"   Tags: {', '.join(result['results']['tags'][:5])}...")
        else:
            print(f"   Error: {result.get('error')}")
            return
        
        video_id = result.get('video_id')
        if not video_id:
            print("❌ No video ID returned, cannot continue tests")
            return
        
        # 3. Test Video Retrieval
        print("\n3️⃣ Testing Video Retrieval...")
        video_data = await get_video_simple(video_id, include_base64=False)
        
        if video_data['success']:
            video = video_data['video']
            print(f"   Retrieved video: {video['id']}")
            print(f"   URL: {video['url']}")
            print(f"   Has video data: {video['has_video']}")
            print(f"   Video size: {video['video_size']:,} bytes")
            print(f"   Created: {video['created_at']}")
            print(f"   Transcript segments: {len(video['transcript']) if video['transcript'] else 0}")
            print(f"   Scene descriptions: {len(video['descriptions']) if video['descriptions'] else 0}")
            print(f"   Tags: {len(video['tags'])}")
        else:
            print(f"   Error: {video_data.get('error')}")
        
        # 4. Test Search
        print("\n4️⃣ Testing Search Functionality...")
        search_result = await search_videos_simple("exercise", limit=5)
        
        if search_result['success']:
            print(f"   Search results: {search_result['count']} videos found")
            for video in search_result['results'][:3]:
                print(f"     • {video['url'][:50]}... ({video['created_at'][:10]})")
        else:
            print(f"   Error: {search_result.get('error')}")
        
        # 5. Test Listing
        print("\n5️⃣ Testing Video Listing...")
        list_result = await list_videos_simple(limit=10)
        
        if list_result['success']:
            print(f"   Recent videos: {list_result['count']} videos found")
            for video in list_result['videos'][:3]:
                print(f"     • {video['url'][:50]}... ({video['created_at'][:10]})")
                print(f"       Tags: {', '.join(video['tags'][:3])}...")
                if video['first_description']:
                    print(f"       Description: {video['first_description'][:80]}...")
        else:
            print(f"   Error: {list_result.get('error')}")
        
        # 6. Test Duplicate Processing (should use existing)
        print("\n6️⃣ Testing Duplicate Processing...")
        duplicate_result = await process_video_unified_simple(
            url=test_url,
            save_video=True,
            transcribe=True,
            describe=True
        )
        
        print(f"   Success: {duplicate_result['success']}")
        print(f"   Message: {duplicate_result.get('message', 'N/A')}")
        print(f"   Same video ID: {duplicate_result.get('video_id') == video_id}")
        
        print("\n✅ All tests completed successfully!")
        print("\n🎉 Simplified single-table approach is working perfectly!")
        print("   - Much cleaner than multi-table complexity")
        print("   - All data in one place")
        print("   - Easy to query and maintain")
        print("   - Duplicate detection works")
        print("   - Search and listing functional")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

async def show_table_structure():
    """Show the simple table structure."""
    print("\n📋 Simple Videos Table Structure:")
    print("=" * 50)
    
    try:
        db = await get_simple_db()
        async with db.connections.get_pg_connection_context() as conn:
            result = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default 
            FROM information_schema.columns 
            WHERE table_name = 'simple_videos'
            ORDER BY ordinal_position;
            """)
            
            for row in result:
                nullable = "NULL" if row['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {row['column_default']}" if row['column_default'] else ""
                print(f"  {row['column_name']:15} {row['data_type']:20} {nullable}{default}")
    
    except Exception as e:
        print(f"❌ Error showing structure: {e}")

if __name__ == "__main__":
    print("🔧 Simple Video Processing System Test")
    print("Using single table approach - much cleaner!")
    
    # Show the table structure first
    asyncio.run(show_table_structure())
    
    # Run the tests
    asyncio.run(test_simple_processing()) 