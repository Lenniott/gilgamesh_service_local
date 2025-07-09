import asyncio
from app.simple_db_operations import SimpleVideoDatabase

VIDEO_ID = "dac8f640-d36b-4c6c-bf89-068c2e1220bf"

async def main():
    db = SimpleVideoDatabase()
    await db.initialize()
    
    if db.connections and db.connections.pg_pool:
        conn = await db.connections.pg_pool.acquire()
        try:
            # Check the video directly
            query = """
                SELECT id, url, carousel_index, 
                       video_base64 IS NOT NULL as has_base64,
                       video_metadata IS NULL as has_no_metadata,
                       video_metadata = '{}'::jsonb as has_empty_metadata,
                       clip_storage_version
                FROM simple_videos 
                WHERE id = $1
            """
            result = await conn.fetchrow(query, VIDEO_ID)
            
            if result:
                print(f"Video found in database:")
                print(f"  ID: {result['id']}")
                print(f"  URL: {result['url']}")
                print(f"  Carousel Index: {result['carousel_index']}")
                print(f"  Has base64: {result['has_base64']}")
                print(f"  Has no metadata: {result['has_no_metadata']}")
                print(f"  Has empty metadata: {result['has_empty_metadata']}")
                print(f"  Clip storage version: {result['clip_storage_version']}")
                
                # Check if it would be selected by migration query
                migration_query = """
                    SELECT COUNT(*) 
                    FROM simple_videos 
                    WHERE id = $1
                    AND video_base64 IS NOT NULL 
                    AND (video_metadata IS NULL OR video_metadata = '{}'::jsonb)
                """
                count_result = await conn.fetchrow(migration_query, VIDEO_ID)
                print(f"  Would be selected by migration: {count_result['count'] > 0}")
            else:
                print(f"Video {VIDEO_ID} not found in database")
                
        finally:
            await db.connections.pg_pool.release(conn)

if __name__ == "__main__":
    asyncio.run(main()) 