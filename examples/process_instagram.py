import asyncio
import os
import json
from pathlib import Path
from app.services.download import AsyncDownloadService
from app.services.scene_processing import SceneProcessingService
from app.services.transcription import TranscriptionService
from app.models.common import VideoMetadata, ProcessingStatusEnum
from app.core.errors import ProcessingError

async def process_video(url: str) -> None:
    """
    Process a video from a URL (Instagram or YouTube).
    
    Args:
        url: URL of the video to process
    """
    print(f"Processing video: {url}")
    
    try:
        # Initialize services
        download_service = AsyncDownloadService()
        scene_service = SceneProcessingService(
            threshold=0.22,  # Scene detection threshold
            target_width=640,  # Target width for optimized video
            target_bitrate="800k"  # Target bitrate for compression
        )
        
        # 1. Download video
        print("1. Downloading video...")
        download_result = await download_service.download_media(url)
        
        if not download_result.video_files:
            raise ProcessingError("No video files found in download result")
            
        video_path = download_result.video_files[0]
        print(f"Downloaded to: {video_path}")
        
        # 2. Process video
        print("\n2. Detecting scenes...")
        result = await scene_service.process_video(video_path)
        
        # 3. Print results
        print("\n3. Processing complete!")
        print(f"Found {len(result['scenes'])} scenes")
        print(f"Video metadata: {result['metadata']}")
        print(f"Optimized video size: {result['video_size'] / 1024 / 1024:.2f} MB")
        
        # Print scene information
        print("\nScene breakdown:")
        for i, scene in enumerate(result['scenes'], 1):
            print(f"\nScene {i}:")
            print(f"  Time: {scene['start_time']:.2f}s - {scene['end_time']:.2f}s")
            if scene['text']:
                print(f"  Text: {scene['text']}")
            print(f"  Confidence: {scene['confidence']:.2f}")
            
        # Save results
        output_path = os.path.join(os.path.dirname(video_path), "scenes.json")
        print(f"\nResults saved to: {output_path}")
        
    except Exception as e:
        print(f"Error processing video: {str(e)}")
        raise

def main():
    import sys
    if len(sys.argv) != 2:
        print("Usage: python process_video.py <video_url>")
        sys.exit(1)
        
    url = sys.argv[1]
    asyncio.run(process_video(url))

if __name__ == "__main__":
    main() 