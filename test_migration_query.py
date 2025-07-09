import asyncio
from app.simple_db_operations import SimpleVideoDatabase

async def main():
    db = SimpleVideoDatabase()
    await db.initialize()
    
    if db.connections and db.connections.pg_pool:
        conn = await db.connections.pg_pool.acquire()
        try:
            # Test the migration query directly
            query = """
                SELECT id, url, carousel_index, video_base64, descriptions, transcript, metadata
                FROM simple_videos 
                WHERE video_base64 IS NOT NULL 
                AND (video_metadata IS NULL OR video_metadata = '{}'::jsonb)
                ORDER BY created_at DESC
                LIMIT 3
            """
            
            result = await conn.fetch(query)
            print(f"Migration query returned {len(result)} videos:")
            
            for i, row in enumerate(result):
                print(f"\nVideo {i+1}:")
                print(f"  ID: {row['id']}")
                print(f"  URL: {row['url']}")
                print(f"  Carousel Index: {row['carousel_index']}")
                print(f"  Has base64: {bool(row['video_base64'])}")
                print(f"  Has descriptions: {bool(row['descriptions'])}")
                
                # Check if our target video is in the results
                if row['id'] == "dac8f640-d36b-4c6c-bf89-068c2e1220bf":
                    print("  *** TARGET VIDEO FOUND ***")
                
        finally:
            await db.connections.pg_pool.release(conn)

if __name__ == "__main__":
    asyncio.run(main()) 