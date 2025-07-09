import asyncio
from app.migration_tools import MigrationManager

async def main():
    mgr = MigrationManager()
    await mgr.initialize()
    videos = await mgr.get_videos_for_migration()
    if videos:
        first = videos[0]
        print("First video eligible for migration:")
        print(f"ID: {first['id']}")
        print(f"URL: {first['url']}")
        print(f"Carousel Index: {first['carousel_index']}")
        print(f"Has base64: {bool(first['video_base64'])}")
        descriptions = first['descriptions']
        if descriptions and isinstance(descriptions, str):
            try:
                import json
                parsed_descriptions = json.loads(descriptions)
                scene_count = len(parsed_descriptions) if isinstance(parsed_descriptions, list) else 0
            except:
                scene_count = "JSON parse error"
        else:
            scene_count = len(descriptions) if descriptions else 0
        print(f"Scene count: {scene_count}")
    else:
        print("No videos found for migration.")

if __name__ == "__main__":
    asyncio.run(main()) 