import asyncio
import os
from pathlib import Path
from app.services.scene_processing import SceneProcessingService
from app.services.transcription import TranscriptionService
from app.models.common import VideoMetadata, ProcessingStatusEnum

async def process_video(video_path: str, output_dir: str = "output"):
    """
    Process a video file to detect scenes and transcribe speech.
    
    Args:
        video_path: Path to the video file
        output_dir: Directory to save output files
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize services
    scene_service = SceneProcessingService(
        threshold=0.22  # Scene detection sensitivity (0.0 to 1.0)
    )
    
    transcription_service = TranscriptionService(
        model_size="base"  # Use base model for faster processing
    )
    
    # Get video metadata
    metadata = VideoMetadata(
        duration=None,  # Will be updated by scene detection
        width=None,
        height=None,
        format="mp4",
        fps=None,
        size_bytes=os.path.getsize(video_path)
    )
    
    print(f"Processing video: {video_path}")
    print("1. Detecting scenes...")
    
    # Detect scenes
    scenes = await scene_service.process_video(video_path, metadata)
    print(f"Found {len(scenes)} scenes:")
    for i, scene in enumerate(scenes, 1):
        print(f"  Scene {i}: {scene.start_time:.2f}s - {scene.end_time:.2f}s")
        if scene.onscreen_text:
            print(f"    Text: {scene.onscreen_text}")
        print(f"    Confidence: {scene.confidence:.2%}")
    
    print("\n2. Transcribing speech...")
    
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
        print(f"[{segment.start:.2f}s - {segment.end:.2f}s] {segment.text}")
        if segment.confidence:
            print(f"  Confidence: {segment.confidence:.2%}")
    
    # Save results to file
    output_file = os.path.join(output_dir, "results.txt")
    with open(output_file, "w") as f:
        f.write("Video Processing Results\n")
        f.write("=======================\n\n")
        
        f.write("Scenes:\n")
        for i, scene in enumerate(scenes, 1):
            f.write(f"Scene {i}: {scene.start_time:.2f}s - {scene.end_time:.2f}s\n")
            if scene.onscreen_text:
                f.write(f"  Text: {scene.onscreen_text}\n")
            f.write(f"  Confidence: {scene.confidence:.2%}\n\n")
        
        f.write("\nTranscript:\n")
        for segment in transcript:
            f.write(f"[{segment.start:.2f}s - {segment.end:.2f}s] {segment.text}\n")
            if segment.confidence:
                f.write(f"  Confidence: {segment.confidence:.2%}\n")
    
    print(f"\nResults saved to: {output_file}")

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Process a video file to detect scenes and transcribe speech")
    parser.add_argument("video_path", help="Path to the video file")
    parser.add_argument("--output-dir", default="output", help="Directory to save output files")
    args = parser.parse_args()
    
    await process_video(args.video_path, args.output_dir)

if __name__ == "__main__":
    asyncio.run(main()) 