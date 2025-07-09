import asyncio
import json
from app.migration_tools import MigrationManager

async def main():
    mgr = MigrationManager()
    await mgr.initialize()
    videos = await mgr.get_videos_for_migration()
    
    print(f"Found {len(videos)} videos for migration")
    print("\n" + "="*80)
    
    # Check first 5 videos
    for i, video in enumerate(videos[:5]):
        print(f"\nVideo {i+1}:")
        print(f"  ID: {video['id']}")
        print(f"  URL: {video['url']}")
        print(f"  Carousel Index: {video['carousel_index']}")
        
        descriptions = video.get('descriptions')
        if descriptions:
            print(f"  Descriptions type: {type(descriptions)}")
            print(f"  Descriptions length: {len(descriptions)}")
            
            # Check if it's a list or string
            if isinstance(descriptions, list):
                print(f"  First item type: {type(descriptions[0]) if descriptions else 'N/A'}")
                if descriptions:
                    print(f"  First item: {descriptions[0]}")
                    print(f"  First item keys: {list(descriptions[0].keys()) if isinstance(descriptions[0], dict) else 'N/A'}")
            elif isinstance(descriptions, str):
                print(f"  String length: {len(descriptions)}")
                print(f"  First 200 chars: {descriptions[:200]}...")
            else:
                print(f"  Unexpected type: {type(descriptions)}")
        else:
            print("  No descriptions field")
        
        print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main()) 