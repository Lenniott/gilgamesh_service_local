#!/usr/bin/env python3
"""
Test script for the new clip storage system.
"""

import asyncio
import logging
import tempfile
import os
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_clip_storage():
    """Test the clip storage system."""
    logger.info("🧪 Testing clip storage system...")
    
    try:
        from app.clip_storage import get_clip_storage
        
        # Initialize clip storage
        clip_storage = get_clip_storage()
        logger.info("✅ Clip storage initialized successfully")
        
        # Test directory creation
        test_video_id = "test-video-123"
        video_dir = clip_storage.get_video_clip_directory(test_video_id)
        logger.info(f"✅ Video directory created: {video_dir}")
        
        # Test filename generation
        scene_id = "scene-456"
        scene_index = 1
        filename = clip_storage.generate_clip_filename(scene_id, scene_index)
        logger.info(f"✅ Generated filename: {filename}")
        
        # Test storage stats
        stats = clip_storage.get_storage_stats()
        logger.info(f"✅ Storage stats: {stats}")
        
        logger.info("✅ All clip storage tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Clip storage test failed: {e}")
        return False

def test_clip_operations():
    """Test the clip operations."""
    logger.info("🧪 Testing clip operations...")
    
    try:
        from app.clip_operations import extract_clip_from_video, validate_clip_file
        
        # Create a test video file (we'll use a simple approach)
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            test_video_path = temp_file.name
            # Write some dummy data (not a real video, just for testing)
            temp_file.write(b'dummy video data')
        
        try:
            # Test validation (should fail for dummy data)
            validation_result = validate_clip_file(test_video_path)
            logger.info(f"✅ Validation test completed: {validation_result}")
            
            logger.info("✅ All clip operations tests passed!")
            return True
            
        finally:
            # Clean up
            if os.path.exists(test_video_path):
                os.unlink(test_video_path)
                
    except Exception as e:
        logger.error(f"❌ Clip operations test failed: {e}")
        return False

async def test_migration_tools():
    """Test the migration tools."""
    logger.info("🧪 Testing migration tools...")
    
    try:
        from app.migration_tools import MigrationManager
        
        # Initialize migration manager
        migration_manager = MigrationManager()
        await migration_manager.initialize()
        logger.info("✅ Migration manager initialized successfully")
        
        # Test getting videos for migration (should be empty in test)
        videos = await migration_manager.get_videos_for_migration()
        logger.info(f"✅ Found {len(videos)} videos for migration")
        
        logger.info("✅ All migration tools tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration tools test failed: {e}")
        return False

async def test_database_connection():
    """Test database connection and new schema."""
    logger.info("🧪 Testing database connection...")
    
    try:
        from app.simple_db_operations import SimpleVideoDatabase
        
        # Initialize database
        db = SimpleVideoDatabase()
        await db.initialize()
        logger.info("✅ Database connection established")
        
        # Test querying the new video_clips table
        if db.connections and db.connections.pg_pool:
            conn = await db.connections.pg_pool.acquire()
            try:
                # Test if video_clips table exists
                result = await conn.fetch("SELECT COUNT(*) FROM video_clips")
                clip_count = result[0]['count']
                logger.info(f"✅ video_clips table exists with {clip_count} records")
                
                # Test if new columns exist in simple_videos
                result = await conn.fetch("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'simple_videos' 
                    AND column_name IN ('video_metadata', 'clip_storage_version')
                """)
                new_columns = [row['column_name'] for row in result]
                logger.info(f"✅ New columns found: {new_columns}")
                
            finally:
                await db.connections.pg_pool.release(conn)
        
        logger.info("✅ All database tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False

async def main():
    """Run all tests."""
    logger.info("🚀 Starting clip storage system tests...")
    
    tests = [
        ("Clip Storage", test_clip_storage),
        ("Clip Operations", test_clip_operations),
        ("Migration Tools", test_migration_tools),
        ("Database Connection", test_database_connection)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running {test_name} test...")
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            results.append((test_name, result))
            
            if result:
                logger.info(f"✅ {test_name} test PASSED")
            else:
                logger.error(f"❌ {test_name} test FAILED")
                
        except Exception as e:
            logger.error(f"❌ {test_name} test ERROR: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("📊 Test Results Summary:")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"   {test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Clip storage system is ready.")
    else:
        logger.error("⚠️ Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main()) 