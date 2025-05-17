import os
import sys
import json
import uuid
from typing import Dict, List, Optional, Union
from app.downloaders import download_media_and_metadata
from app.scene_detection import extract_scene_cuts_and_frames, get_video_duration
from app.ocr_utils import ocr_image, EASYOCR_READER
from app.transcription import transcribe_audio
from app.video_processing import extract_and_downscale_scene, cleanup_temp_files
from app.utils import clean_text, resize_image_if_needed

DEFAULT_SCENE_THRESHOLD = 0.22

def process_single_url(url: str, threshold: float = DEFAULT_SCENE_THRESHOLD, encode_base64: bool = True) -> Dict:
    """
    Process a single URL and return a standardized response.
    
    Args:
        url: The URL to process (Instagram post/carousel/reel or YouTube)
        threshold: Scene detection threshold (default: 0.22)
        encode_base64: Whether to include base64-encoded media in the response (default: True)
        
    Returns:
        Dict containing:
        {
            "url": str,
            "title": str,
            "description": str,
            "tags": List[str],
            "videos": Optional[List[Dict]],  # For posts with videos/reels
            "images": Optional[List[Dict]]   # For posts with images
        }
        
    Raises:
        Exception: If processing fails for any reason
    """
    # Create a unique temp directory for this URL
    temp_dir = os.path.join(os.path.dirname(__file__), 'temp', str(uuid.uuid4()))
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # Download media and metadata
        result = download_media_and_metadata(url)
        result['temp_dir'] = temp_dir  # Override temp_dir with our UUID-based one
        
        # Process media files
        video_files = [f for f in result['files'] if f.lower().endswith(('.mp4', '.mkv', '.webm'))]
        image_files = [f for f in result['files'] if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        # Process videos
        videos_output = []
        for video_file in video_files:
            video_result = process_video(video_file, result, threshold, encode_base64)
            if video_result:
                videos_output.append(video_result)
        
        # Process images
        images_output = []
        for image_file in image_files:
            image_result = process_image(image_file, result, encode_base64)
            if image_result:
                images_output.append(image_result)
        
        # Build final response
        response = {
            "url": url,
            "title": result.get('title', ''),
            "description": result.get('description', ''),
            "tags": result.get('tags', []),
        }
        
        if videos_output:
            response["videos"] = videos_output
        if images_output:
            response["images"] = images_output
            
        return response
        
    except Exception as e:
        # Clean up temp directory on error
        cleanup_temp_files(temp_dir)
        raise e

def process_video(video_file: str, result: Dict, threshold: float, encode_base64: bool = True) -> Optional[Dict]:
    """Process a single video file and return its data."""
    try:
        video_name = os.path.splitext(os.path.basename(video_file))[0]
        frames_dir = os.path.join(result['temp_dir'], 'frames', video_name)
        os.makedirs(frames_dir, exist_ok=True)
        
        # Get transcript
        try:
            transcript = transcribe_audio(video_file)
        except Exception as e:
            print(f"Warning: Could not transcribe video {video_file}: {e}")
            transcript = []
            
        # Get scenes
        try:
            scene_cuts = extract_scene_cuts_and_frames(video_file, frames_dir, threshold=threshold)
        except Exception as e:
            print(f"Warning: Could not extract scenes from video {video_file}: {e}")
            scene_cuts = []
            
        # Process scenes
        scenes = []
        for start, frame in scene_cuts:
            end = get_video_duration(video_file) if start == scene_cuts[-1][0] else scene_cuts[scene_cuts.index((start, frame)) + 1][0]
            
            # Get OCR text for the frame
            try:
                ocr_text = ocr_image(frame, reader=EASYOCR_READER)
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
                    scene_base64 = extract_and_downscale_scene(video_file, start, end, target_width=480)
                    scene_data["video"] = scene_base64
                except Exception as e:
                    print(f"Warning: Could not extract scene {start}-{end}: {e}")
                    scene_data["video"] = None
                
            scenes.append(scene_data)
            
        return {
            "id": str(uuid.uuid4()),
            "scenes": scenes,
            "transcript": transcript
        }
        
    except Exception as e:
        print(f"Error processing video {video_file}: {e}")
        return None

def process_image(image_file: str, result: Dict, encode_base64: bool = True) -> Optional[Dict]:
    """Process a single image file and return its data."""
    try:
        ocr_text = ocr_image(image_file, reader=EASYOCR_READER)
        image_data = {
            "text": ocr_text
        }
        
        # Only include base64 data if encode_base64 is True
        if encode_base64:
            try:
                with open(image_file, 'rb') as f:
                    import base64
                    image_data["base64"] = base64.b64encode(f.read()).decode('utf-8')
            except Exception as e:
                print(f"Warning: Could not encode image {image_file}: {e}")
                image_data["base64"] = None
                
        return image_data
    except Exception as e:
        print(f"Error processing image {image_file}: {e}")
        return None

def process_and_cleanup(url: str, threshold: float = DEFAULT_SCENE_THRESHOLD) -> Dict:
    """
    Process a URL and clean up temporary files.
    
    Args:
        url: The URL to process
        threshold: Scene detection threshold
        
    Returns:
        Dict containing the processed result
    """
    try:
        result = process_single_url(url, threshold)
        return result
    finally:
        # Cleanup is handled by process_single_url's temp directory management
        pass

def main():
    if len(sys.argv) < 2:
        print('Usage: python media_utils.py <url> [threshold]')
        sys.exit(1)
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_SCENE_THRESHOLD
    process_and_cleanup(sys.argv[1], threshold)

if __name__ == '__main__':
    main()
