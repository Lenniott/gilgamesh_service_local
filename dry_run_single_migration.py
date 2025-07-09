import asyncio
from app.migration_tools import MigrationManager

VIDEO_ID = "dac8f640-d36b-4c6c-bf89-068c2e1220bf"

async def main():
    mgr = MigrationManager()
    await mgr.initialize()
    videos = await mgr.get_videos_for_migration()
    
    if not videos:
        print("No videos found for migration.")
        return
    
    # Use the first video from the migration results
    video = videos[0]
    print(f"Running dry run migration for video: {video['id']}")
    print(f"URL: {video['url']}")
    print(f"Carousel Index: {video['carousel_index']}")
    
    result = await mgr.migrate_video(video)
    print("\n--- Dry Run Migration Result ---")
    for k, v in result.items():
        if k == 'clip_paths' and isinstance(v, list):
            print(f"{k}: {len(v)} clips")
            for i, path in enumerate(v[:3]):  # Show first 3 paths
                print(f"  Clip {i+1}: {path}")
        else:
            print(f"{k}: {v}")

if __name__ == "__main__":
    asyncio.run(main()) 