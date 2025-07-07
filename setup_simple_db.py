#!/usr/bin/env python3
"""
Setup script for the simplified video database.
Creates the simple_videos table and tests connections.
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.append('app')

async def setup_database():
    """Setup the simplified database and test connections."""
    
    print("🔧 Setting up Simplified Video Database")
    print("=" * 50)
    
    try:
        from app.db_connections import get_db_connections
        
        # Get database connections
        print("1️⃣ Connecting to databases...")
        db = await get_db_connections()
        
        # Test connections
        connections = await db.test_all_connections()
        print(f"   📊 PostgreSQL: {'✅' if connections.get('postgresql') else '❌'}")
        print(f"   🔍 Qdrant: {'✅' if connections.get('qdrant') else '❌'}")
        
        if not connections.get('postgresql'):
            print("❌ PostgreSQL connection failed!")
            return False
        
        # Create the simple_videos table
        print("\n2️⃣ Creating simple_videos table...")
        
        conn = await db.pg_pool.acquire()
        try:
            # Create table
            await conn.execute('''
            CREATE TABLE IF NOT EXISTS simple_videos (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                url TEXT NOT NULL,
                video_base64 TEXT,
                transcript JSONB,
                descriptions JSONB,
                tags TEXT[],
                metadata JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT simple_videos_url_key UNIQUE (url)
            );
            ''')
            
            print("   ✅ Table created successfully")
            
            # Create indexes
            await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_simple_videos_url ON simple_videos(url);
            CREATE INDEX IF NOT EXISTS idx_simple_videos_tags ON simple_videos USING GIN(tags);
            CREATE INDEX IF NOT EXISTS idx_simple_videos_transcript ON simple_videos USING GIN(transcript);
            CREATE INDEX IF NOT EXISTS idx_simple_videos_descriptions ON simple_videos USING GIN(descriptions);
            CREATE INDEX IF NOT EXISTS idx_simple_videos_created_at ON simple_videos(created_at);
            ''')
            
            print("   ✅ Indexes created successfully")
            
            # Create update trigger
            await conn.execute('''
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
            ''')
            
            await conn.execute('''
            DROP TRIGGER IF EXISTS update_simple_videos_updated_at ON simple_videos;
            CREATE TRIGGER update_simple_videos_updated_at 
                BEFORE UPDATE ON simple_videos 
                FOR EACH ROW 
                EXECUTE FUNCTION update_updated_at_column();
            ''')
            
            print("   ✅ Update trigger created successfully")
            
            # Test insert and retrieval
            print("\n3️⃣ Testing database operations...")
            
            # Test insert
            test_id = await conn.fetchval('''
            INSERT INTO simple_videos (url, metadata) 
            VALUES ($1, $2) 
            ON CONFLICT ON CONSTRAINT simple_videos_url_key DO UPDATE SET metadata = EXCLUDED.metadata
            RETURNING id;
            ''', 'https://test.com/video', '{"test": true}')
            
            print(f"   ✅ Test insert successful: {test_id}")
            
            # Test select
            result = await conn.fetchrow('''
            SELECT id, url, metadata, created_at FROM simple_videos WHERE id = $1;
            ''', test_id)
            
            if result:
                print(f"   ✅ Test select successful: {result['url']}")
            else:
                print("   ❌ Test select failed")
                return False
            
            # Clean up test data
            await conn.execute('DELETE FROM simple_videos WHERE url = $1', 'https://test.com/video')
            print("   ✅ Test data cleaned up")
            
        finally:
            await db.pg_pool.release(conn)
        
        print("\n🎉 Database setup completed successfully!")
        print("   • simple_videos table ready")
        print("   • Indexes optimized for performance")  
        print("   • Auto-update trigger configured")
        print("   • Database operations tested")
        
        return True
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_simple_db_operations():
    """Test the simplified database operations."""
    
    print("\n🧪 Testing Simple Database Operations")
    print("=" * 50)
    
    try:
        from app.simple_db_operations import get_simple_db
        
        # Get database instance
        db = await get_simple_db()
        
        # Test connection
        await db.initialize()
        
        if not db.connections or not db.connections.pg_pool:
            print("❌ Database connection failed")
            return False
        
        print("✅ Database connection successful")
        
        # Test basic operations without actual video file
        print("✅ Simple database operations ready")
        
        return True
        
    except Exception as e:
        print(f"❌ Database operations test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main setup function."""
    
    # Setup database
    db_success = await setup_database()
    
    if db_success:
        # Test operations
        ops_success = await test_simple_db_operations()
        
        if ops_success:
            print("\n🎉 All setup completed successfully!")
            print("You can now run: python test_simple_system.py")
        else:
            print("\n❌ Operations test failed")
    else:
        print("\n❌ Database setup failed")

if __name__ == "__main__":
    asyncio.run(main()) 