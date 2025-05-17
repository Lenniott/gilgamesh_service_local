import asyncio
import json
from pathlib import Path
from app.services.download import AsyncDownloadService
from app.services.scene_processing import SceneProcessingService
from app.core.errors import ProcessingError
import re

async def process_url(url: str, download_service: AsyncDownloadService, processing_service: SceneProcessingService):
    """Process a single URL and return the results."""
    try:
        print(f"\nProcessing URL: {url}")
        print("-" * 80)
        
        # Download the media
        download_result = await download_service.download_media(url)
        print(f"Downloaded media")
        print(f"Source: {download_result.metadata.source}")
        print(f"Media type: {download_result.metadata.media_type}")
        print(f"Media count: {download_result.metadata.media_count}")
        
        # Prepare output directory
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # Sanitize URL for filename
        def sanitize(s):
            return re.sub(r'[^a-zA-Z0-9]+', '_', s)
        url_id = sanitize(url)
        
        # Process each media file
        results = []
        for idx, media_path in enumerate(download_result.files):
            # Process based on media type from metadata
            if download_result.metadata.media_type == 'image':
                result = await processing_service.process_media(media_path, 'image')
            else:  # video
                result = await processing_service.process_media(media_path, 'video')
            results.append(result)
            
            # Print the JSON output
            print("\nJSON Output:")
            print(json.dumps(result, indent=2))
            
            # Save JSON output to file
            media_basename = Path(media_path).stem
            output_path = output_dir / f"{url_id}_{media_basename}.json"
            with open(output_path, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Saved JSON output to {output_path}")
        
        return results
        
    except ProcessingError as e:
        print(f"Error processing {url}: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error processing {url}: {str(e)}")
        return None

async def main():
    # Initialize services
    download_service = AsyncDownloadService()
    processing_service = SceneProcessingService()
    
    # Test URLs
    urls = [
        "https://www.instagram.com/p/DJRiA-gI2GT/?igsh=bXI4MWJzNnhhMm5t",
        "https://www.instagram.com/reel/DJVTMdRxRmJ/?igsh=eHJtN214OWpuMnIx",
        "https://youtube.com/shorts/izeO1Vpqvvo?si=blnnaTO0uYEe5htC",
        "https://www.instagram.com/p/DJpP_JPSKHK/?igsh=MmIyb2twNXc0ajNv"
    ]
    
    # Process each URL
    for url in urls:
        await process_url(url, download_service, processing_service)
        print("\n" + "=" * 80 + "\n")

if __name__ == "__main__":
    asyncio.run(main()) 