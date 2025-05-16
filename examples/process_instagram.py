import asyncio
import os
import json
from pathlib import Path
from app.services.download import AsyncDownloadService
from app.services.scene_processing import SceneProcessingService
from app.services.transcription import TranscriptionService
from app.models.common import VideoMetadata, ProcessingStatusEnum

async def process_instagram_reel(url: str, output_dir: str = "output"):
    """
    Process an Instagram reel to detect scenes and transcribe speech.
    
    Args:
        url: Instagram reel URL
        output_dir: Directory to save output files
    """
    print(f"Processing Instagram reel: {url}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print("1. Downloading reel...")
    
    # Initialize download service
    download_service = AsyncDownloadService()
    
    try:
        # Download the reel
        download_result = await download_service.download_media(url)
        
        if not download_result.files:
            print("No video files found in the download")
            return
            
        # Get the video file (should be the first file)
        video_path = download_result.files[0]
        print(f"Downloaded to: {video_path}")
        
        # Initialize services
        scene_service = SceneProcessingService(
            threshold=0.22,  # Scene detection sensitivity (0.0 to 1.0)
            frame_delay=0.5,  # Wait 0.5s after scene cut before taking frame
            target_width=640,  # Downscale to 640px width
            target_bitrate="800k"  # Target bitrate for compression
        )
        
        transcription_service = TranscriptionService(
            model_size="base"  # Use base model for faster processing
        )
        
        # Get video metadata
        metadata = VideoMetadata(
            duration=download_result.metadata.duration,  # Use duration from download result
            width=None,
            height=None,
            format="mp4",
            fps=None,
            size_bytes=os.path.getsize(video_path)
        )
        
        print("\n2. Detecting scenes...")
        
        # Detect scenes
        scene_result = await scene_service.process_video(video_path, metadata)
        scenes = scene_result["scenes"]
        print(f"Found {len(scenes)} scenes:")
        for i, scene in enumerate(scenes, 1):
            print(f"  Scene {i}: {scene['start']:.2f}s - {scene['end']:.2f}s")
            if scene['text']:
                print(f"    Text: {scene['text']}")
            print(f"    Confidence: {scene['confidence']:.1%}")
        
        print("\n3. Transcribing speech...")
        
        # Track progress
        async def progress_callback(progress: float):
            print(f"  Progress: {progress:.1f}%", end="\r")
        
        # Transcribe video
        transcript = await transcription_service.transcribe_video(
            video_path,
            progress_callback=progress_callback
        )
        
        print("\nTranscription complete!")
        print("\nTranscript:")
        for segment in transcript:
            print(f"  {segment.start:.2f}s - {segment.end:.2f}s: {segment.text}")
        
        # Save results
        output = {
            "url": url,
            "title": download_result.metadata.title,
            "description": download_result.metadata.description,
            "tags": download_result.metadata.tags,
            "upload_date": download_result.metadata.upload_date,
            "scenes": scenes,
            "transcript": [{"start": s.start, "end": s.end, "text": s.text} for s in transcript],
            "metadata": scene_result["metadata"],
            "video_base64": scene_result["video_base64"]
        }
        
        output_path = os.path.join(output_dir, "result.json")
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)
        
        print(f"\nResults saved to: {output_path}")
        print(f"Video size: {scene_result['metadata']['size_bytes'] / 1024 / 1024:.1f} MB")
        print(f"Resolution: {scene_result['metadata']['resolution']}")
        
    except Exception as e:
        print(f"Error processing reel: {str(e)}")
    finally:
        # Cleanup temporary files
        await download_service.cleanup_old_downloads(max_age_hours=0)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python process_instagram.py <instagram_reel_url>")
        sys.exit(1)
        
    url = sys.argv[1]
    asyncio.run(process_instagram_reel(url)) 