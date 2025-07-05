#!/usr/bin/env python3
"""
Safe script to clear Gilgamesh test data from the database.
Only clears the simple_videos table - leaves all other data intact.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the app directory to Python path
sys.path.append('app')

async def clear_test_data():
    """Clear only the Gilgamesh test data from the database."""
    
    print("🧹 Clearing Gilgamesh Test Data")
    print("=" * 50)
    
    try:
        from app.simple_db_operations import SimpleVideoDatabase
        
        # Initialize database
        print("1️⃣ Connecting to database...")
        db = SimpleVideoDatabase()
        if not await db.initialize():
            print("❌ Failed to connect to database!")
            return False
        
        # Check current data
        print("\n2️⃣ Checking current data...")
        conn = await db.connections.pg_pool.acquire()
        try:
            # Count current videos
            count = await conn.fetchval("SELECT COUNT(*) FROM simple_videos")
            print(f"   📊 Current videos in database: {count}")
            
            if count == 0:
                print("   ✅ Database is already empty!")
                return True
            
            # Show sample data
            sample = await conn.fetch("""
                SELECT id, url, carousel_index, created_at 
                FROM simple_videos 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            
            print("   🔍 Sample entries to be deleted:")
            for row in sample:
                print(f"     - {row['url']} (carousel_index: {row['carousel_index']}) - {row['created_at']}")
            
            # Confirm deletion
            print(f"\n3️⃣ Ready to delete {count} videos from simple_videos table...")
            print("   ⚠️  This will permanently delete all video data!")
            print("   ✅ Other tables (n8n, workflows, etc.) will NOT be affected")
            
            # For safety, require explicit confirmation
            if len(sys.argv) > 1 and sys.argv[1] == "--confirm":
                print("\n   🗑️  Deleting all videos...")
                
                # Delete all videos
                deleted_count = await conn.fetchval("DELETE FROM simple_videos RETURNING COUNT(*)")
                print(f"   ✅ Successfully deleted {deleted_count} videos")
                
                # Verify deletion
                remaining = await conn.fetchval("SELECT COUNT(*) FROM simple_videos")
                if remaining == 0:
                    print("   ✅ Database is now clean!")
                else:
                    print(f"   ⚠️  {remaining} videos still remain")
                
                return True
            else:
                print("\n   ❌ Deletion not confirmed!")
                print("   💡 To actually delete the data, run:")
                print("      python clear_test_data.py --confirm")
                return False
                
        finally:
            await db.connections.pg_pool.release(conn)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def show_safe_alternatives():
    """Show safe alternatives for clearing data."""
    print("\n🔧 Safe Alternatives:")
    print("=" * 30)
    print("1. Clear specific URL:")
    print("   python -c \"import asyncio; from app.simple_db_operations import SimpleVideoDatabase; asyncio.run(clear_url('https://specific-url'))\"")
    print("\n2. Clear recent data (last N days):")
    print("   # Add date filter to DELETE query")
    print("\n3. Backup before clearing:")
    print("   pg_dump -t simple_videos your_database > backup_simple_videos.sql")
    print("\n4. Clear everything (current script):")
    print("   python clear_test_data.py --confirm")

if __name__ == "__main__":
    print("🚨 SAFETY CHECK: This script will only clear the 'simple_videos' table")
    print("   Other tables (n8n workflows, credentials, etc.) will NOT be affected")
    print("   This is safe for your shared database environment\n")
    
    success = asyncio.run(clear_test_data())
    
    if not success:
        asyncio.run(show_safe_alternatives()) 