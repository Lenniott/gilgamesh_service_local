import os
import sys
import json
import uuid
import asyncio
from typing import Dict, List, Optional, Union
from app.downloaders import download_media_and_metadata
from app.scene_detection import extract_scene_cuts_and_frames, get_video_duration
from app.ocr_utils import ocr_image, EASYOCR_READER
from app.transcription import transcribe_audio
from app.video_processing import extract_and_downscale_scene, cleanup_temp_files
from app.utils import clean_text, resize_image_if_needed

DEFAULT_SCENE_THRESHOLD = 0.22

async def process_single_url(url: str, threshold: float = DEFAULT_SCENE_THRESHOLD, encode_base64: bool = True) -> Dict:
    """
    Process a single URL and return a standardized response asynchronously.
    
    Args:
        url: The URL to process (Instagram post/carousel/reel or YouTube)
        threshold: Scene detection threshold (default: 0.22)
        encode_base64: Whether to include base64-encoded video data in the response (default: True)
        
    Returns:
        Dict containing:
        {
            "url": str,
            "title": str,
            "description": str,
            "tags": List[str],
            "videos": Optional[List[Dict]],  # For posts with videos/reels
            "images": Optional[List[Dict]],  # For posts with images
            "temp_dir": str                  # Temporary directory path (for cleanup)
        }
        
    Raises:
        Exception: If processing fails for any reason
    """
    # Create a unique temp directory for this URL
    temp_dir = os.path.join(os.path.dirname(__file__), 'temp', str(uuid.uuid4()))
    await asyncio.to_thread(os.makedirs, temp_dir, exist_ok=True)
    
    try:
        # Download media and metadata
        result = await download_media_and_metadata(url)
        result['temp_dir'] = temp_dir  # Override temp_dir with our UUID-based one
        
        # Process media files
        video_files = [f for f in result['files'] if f.lower().endswith(('.mp4', '.mkv', '.webm'))]
        image_files = [f for f in result['files'] if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        # Process videos concurrently
        video_tasks = [process_video(video_file, result, threshold, encode_base64) for video_file in video_files]
        videos_output = [r for r in await asyncio.gather(*video_tasks) if r]
        
        # Process images concurrently
        image_tasks = [process_image(image_file, result) for image_file in image_files]
        images_output = [r for r in await asyncio.gather(*image_tasks) if r]
        
        # Build final response
        response = {
            "url": url,
            "title": result.get('title', ''),
            "description": result.get('description', ''),
            "tags": result.get('tags', []),
            "temp_dir": temp_dir  # Include temp_dir for cleanup
        }
        
        if videos_output:
            response["videos"] = videos_output
        if images_output:
            response["images"] = images_output
            
        return response
        
    except Exception as e:
        # Clean up temp directory on error
        await asyncio.to_thread(cleanup_temp_files, temp_dir)
        raise e

async def process_video(video_file: str, result: Dict, threshold: float, encode_base64: bool = True) -> Optional[Dict]:
    """Process a single video file and return its data asynchronously."""
    try:
        video_name = os.path.splitext(os.path.basename(video_file))[0]
        frames_dir = os.path.join(result['temp_dir'], 'frames', video_name)
        await asyncio.to_thread(os.makedirs, frames_dir, exist_ok=True)
        
        # Get transcript and scenes concurrently
        async def get_transcript():
            try:
                return await asyncio.to_thread(transcribe_audio, video_file)
            except Exception as e:
                print(f"Warning: Could not transcribe video {video_file}: {e}")
                return []
            
        async def get_scenes():
            try:
                return await asyncio.to_thread(extract_scene_cuts_and_frames, video_file, frames_dir, threshold=threshold)
            except Exception as e:
                print(f"Warning: Could not extract scenes from video {video_file}: {e}")
                return []
        
        transcript, scene_cuts = await asyncio.gather(get_transcript(), get_scenes())
        
        # Process scenes concurrently
        async def process_scene(start_frame):
            start, frame = start_frame
            end = await asyncio.to_thread(get_video_duration, video_file) if start == scene_cuts[-1][0] else scene_cuts[scene_cuts.index((start, frame)) + 1][0]
            
            # Get OCR text for the frame
            try:
                ocr_text = await asyncio.to_thread(ocr_image, frame, reader=EASYOCR_READER)
            except Exception as e:
                print(f"Warning: Could not OCR frame {frame}: {e}")
                ocr_text = ""
                
            scene_data = {
                "start": start,
                "end": end,
                "text": ocr_text,
                "confidence": 1.0,  # TODO: Add actual confidence from OCR
            }
            
            # Only include video data if encode_base64 is True
            if encode_base64:
                try:
                    scene_base64 = await asyncio.to_thread(extract_and_downscale_scene, video_file, start, end, target_width=480)
                    scene_data["video"] = scene_base64
                except Exception as e:
                    print(f"Warning: Could not extract scene {start}-{end}: {e}")
                    scene_data["video"] = None
                
            return scene_data
        
        scenes = await asyncio.gather(*(process_scene(scene) for scene in scene_cuts))
            
        return {
            "id": video_name,
            "scenes": scenes,
            "transcript": transcript
        }
        
    except Exception as e:
        print(f"Error processing video {video_file}: {e}")
        return None

async def process_image(image_file: str, result: Dict) -> Optional[Dict]:
    """Process a single image file and return its data asynchronously."""
    try:
        ocr_text = await asyncio.to_thread(ocr_image, image_file, reader=EASYOCR_READER)
        return {
            "text": ocr_text
        }
    except Exception as e:
        print(f"Error processing image {image_file}: {e}")
        return None

async def process_and_cleanup(url: str, threshold: float = DEFAULT_SCENE_THRESHOLD) -> Dict:
    """
    Process a URL and clean up temporary files asynchronously.
    
    Args:
        url: The URL to process
        threshold: Scene detection threshold
        
    Returns:
        Dict containing the processed result
    """
    try:
        result = await process_single_url(url, threshold)
        return result
    finally:
        # Cleanup is handled by process_single_url's temp directory management
        pass

async def main():
    if len(sys.argv) < 2:
        print('Usage: python media_utils.py <url> [threshold]')
        sys.exit(1)
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_SCENE_THRESHOLD
    await process_and_cleanup(sys.argv[1], threshold)

if __name__ == '__main__':
    asyncio.run(main())
