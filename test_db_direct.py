#!/usr/bin/env python3
"""
Direct database test to isolate the PostgreSQL connection issue.
"""

import asyncio
import sys
import os
import json

# Add the app directory to Python path
sys.path.append('app')

async def test_direct_db_save():
    """Test direct database saving without the complex processor."""
    
    print("🔧 Direct Database Connection Test")
    print("=" * 50)
    
    try:
        # Import here to avoid import issues
        from app.db_connections import get_db_connections
        
        print("1️⃣ Getting fresh database connection...")
        
        # Get a fresh database connection
        db_connections = await get_db_connections()
        
        print("2️⃣ Testing PostgreSQL connection...")
        
        # Test the connection
        conn = await db_connections.pg_pool.acquire()
        
        try:
            # Test basic query
            result = await conn.fetchval("SELECT 1")
            print(f"   ✅ Basic query works: {result}")
            
            # Test table exists
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'simple_videos'
                );
            """)
            print(f"   ✅ Table exists: {table_exists}")
            
            if not table_exists:
                print("   ❌ simple_videos table doesn't exist!")
                return False
            
            # Test insert with real data
            print("3️⃣ Testing video save...")
            
            test_url = "https://test.example.com/video123"
            test_transcript = [
                {"start": 0.0, "end": 5.0, "text": "Test transcript segment"}
            ]
            test_descriptions = [
                {
                    "start_time": 0.0,
                    "end_time": 5.0,
                    "description": "Test scene description",
                    "analysis_success": True
                }
            ]
            test_tags = ["test", "video", "example"]
            test_metadata = {
                "test": True,
                "source": "direct_test"
            }
            
            # Insert test data
            video_id = await conn.fetchval("""
                INSERT INTO simple_videos (
                    url, video_base64, transcript, descriptions, tags, metadata
                ) VALUES (
                    $1, $2, $3, $4, $5, $6
                )
                ON CONFLICT (url) DO UPDATE SET
                    transcript = EXCLUDED.transcript,
                    descriptions = EXCLUDED.descriptions,
                    tags = EXCLUDED.tags,
                    metadata = EXCLUDED.metadata,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id;
            """, 
                test_url,
                "dGVzdCB2aWRlbyBkYXRh",  # "test video data" in base64
                json.dumps(test_transcript),
                json.dumps(test_descriptions),
                test_tags,
                json.dumps(test_metadata)
            )
            
            print(f"   ✅ Video saved successfully: {video_id}")
            
            # Test retrieval
            print("4️⃣ Testing video retrieval...")
            
            result = await conn.fetchrow("""
                SELECT id, url, transcript, descriptions, tags, metadata, created_at
                FROM simple_videos 
                WHERE id = $1
            """, video_id)
            
            if result:
                print(f"   ✅ Video retrieved: {result['url']}")
                print(f"   ✅ Transcript segments: {len(json.loads(result['transcript']))}")
                print(f"   ✅ Descriptions: {len(json.loads(result['descriptions']))}")
                print(f"   ✅ Tags: {result['tags']}")
                print(f"   ✅ Created: {result['created_at']}")
            else:
                print("   ❌ Video retrieval failed")
                return False
            
            # Clean up test data
            await conn.execute("DELETE FROM simple_videos WHERE url = $1", test_url)
            print("   ✅ Test data cleaned up")
            
            print("\n🎉 Direct database test successful!")
            return True
            
        finally:
            await db_connections.pg_pool.release(conn)
            
    except Exception as e:
        print(f"❌ Direct database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_simple_db_class():
    """Test the SimpleVideoDatabase class directly."""
    
    print("\n🔧 Testing SimpleVideoDatabase Class")
    print("=" * 50)
    
    try:
        from app.simple_db_operations import SimpleVideoDatabase
        
        # Create a fresh instance
        db = SimpleVideoDatabase()
        
        print("1️⃣ Initializing database...")
        connections = await db.initialize()
        
        print(f"   📊 PostgreSQL: {'✅' if connections.get('postgresql') else '❌'}")
        print(f"   🔍 Qdrant: {'✅' if connections.get('qdrant') else '❌'}")
        
        if not connections.get('postgresql'):
            print("❌ PostgreSQL initialization failed!")
            return False
        
        print("2️⃣ Testing get_video_by_url (should return None for non-existent)...")
        
        # Test get_video_by_url with non-existent URL
        result = await db.get_video_by_url("https://nonexistent.com/video")
        print(f"   ✅ Non-existent video returns: {result}")
        
        print("3️⃣ Testing connection reuse...")
        
        # Test multiple calls to ensure connection reuse works
        for i in range(3):
            result = await db.get_video_by_url(f"https://test{i}.com/video")
            print(f"   ✅ Call {i+1}: {result is None}")
        
        print("\n🎉 SimpleVideoDatabase class test successful!")
        return True
        
    except Exception as e:
        print(f"❌ SimpleVideoDatabase test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all direct database tests."""
    
    # Test direct database operations
    direct_success = await test_direct_db_save()
    
    if direct_success:
        # Test the SimpleVideoDatabase class
        class_success = await test_simple_db_class()
        
        if class_success:
            print("\n🎉 All database tests passed!")
            print("The database connection is working properly.")
            print("The issue might be in the video processing pipeline.")
        else:
            print("\n❌ SimpleVideoDatabase class has issues")
    else:
        print("\n❌ Direct database operations failed")

if __name__ == "__main__":
    asyncio.run(main()) 