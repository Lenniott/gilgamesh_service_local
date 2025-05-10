import subprocess
import re
from typing import List, Dict
import os
import instaloader
import uuid
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import unicodedata
import yt_dlp
import whisper
import json
import string
import easyocr
import concurrent.futures
import base64

# Default threshold for scene detection (0.4 is a good balance between sensitivity and specificity)
DEFAULT_SCENE_THRESHOLD = 0.22

# Initialize EasyOCR reader once
EASYOCR_READER = easyocr.Reader(['en'], gpu=False)

def detect_scenes(video_path: str, threshold: float = DEFAULT_SCENE_THRESHOLD) -> List[float]:
    """
    Detect scene cuts in a video using ffmpeg. Returns a list of cut times (in seconds).
    """
    # ffmpeg command to detect scene changes
    cmd = [
        'ffmpeg', '-i', video_path,
        '-filter_complex', f"select='gt(scene,{threshold})',showinfo",
        '-f', 'null', '-'
    ]
    result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    # Parse showinfo output for frame pts_time
    cut_times = []
    for line in result.stderr.split('\n'):
        if 'showinfo' in line and 'pts_time:' in line:
            match = re.search(r'pts_time:([0-9.]+)', line)
            if match:
                cut_times.append(float(match.group(1)))
    return cut_times

def preprocess_image(image_path: str) -> Image.Image:
    image = Image.open(image_path).convert('L')
    image = image.filter(ImageFilter.MedianFilter())
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2)
    return image

def clean_text(text: str) -> str:
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'\s+', ' ', text)
    # Remove non-ASCII except basic punctuation
    text = ''.join(c for c in text if c in string.printable)
    return text.strip()

def resize_image_if_needed(image_path: str, max_width: int = 800) -> str:
    image = Image.open(image_path)
    if image.width > max_width:
        ratio = max_width / image.width
        new_size = (max_width, int(image.height * ratio))
        # Use correct resampling filter for Pillow version
        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.LANCZOS  # For older Pillow
        image = image.resize(new_size, resample)
        resized_path = image_path.replace('.jpg', '_resized.jpg').replace('.png', '_resized.png')
        image.save(resized_path)
        return resized_path
    return image_path

def ocr_image(image_path: str, reader=None) -> str:
    # Resize if needed
    image_path = resize_image_if_needed(image_path)
    # Try EasyOCR first
    if reader is None:
        reader = EASYOCR_READER
    try:
        result = reader.readtext(image_path, detail=0)
        text = ' '.join(result)
        text = clean_text(text)
        if text.strip():
            return text
    except Exception as e:
        print(f"Warning: EasyOCR failed on {image_path}: {e}")
    # Fallback to Tesseract
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image, config='--psm 6')
    text = clean_text(text)
    if not text.strip():
        preprocessed = preprocess_image(image_path)
        debug_path = image_path.replace('.jpg', '_preprocessed.jpg').replace('.png', '_preprocessed.png')
        preprocessed.save(debug_path)
        text = pytesseract.image_to_string(preprocessed, config='--psm 6')
        text = clean_text(text)
    return text

def download_instagram_media(url: str, out_dir: str) -> List[str]:
    """
    Download all media (images/videos) from an Instagram post or reel using instaloader.
    If metadata (caption/comment) cannot be fetched, skip it but still download media.
    Returns a list of file paths.
    """
    os.makedirs(out_dir, exist_ok=True)
    L = instaloader.Instaloader(dirname_pattern=out_dir, download_videos=True, save_metadata=False)
    shortcode = url.split('?')[0].rstrip('/').split('/')[-1]
    post = instaloader.Post.from_shortcode(L.context, shortcode)
    L.download_post(post, target=out_dir)
    files = [os.path.join(out_dir, f) for f in os.listdir(out_dir) if f.lower().endswith(('.mp4', '.mkv', '.webm', '.jpg', '.jpeg', '.png'))]
    return files

def extract_scene_cuts_and_frames(video_path: str, out_dir: str, threshold: float = DEFAULT_SCENE_THRESHOLD):
    """
    Use FFmpeg to extract frames at scene changes and return a list of (timestamp, frame_path) tuples.
    Always includes the first frame (timestamp 0.0) in addition to scene changes.
    """
    os.makedirs(out_dir, exist_ok=True)
    
    # First, extract the first frame
    first_frame_path = os.path.join(out_dir, 'cut_0000.jpg')
    first_frame_cmd = [
        'ffmpeg', '-i', video_path,
        '-vf', 'select=eq(n\,0)',
        '-vframes', '1',
        first_frame_path
    ]
    subprocess.run(first_frame_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Then extract frames at scene changes
    frame_pattern = os.path.join(out_dir, 'cut_%04d.jpg')
    cmd = [
        'ffmpeg', '-i', video_path,
        '-vf', f"select='gt(scene,{threshold})',showinfo",
        '-vsync', 'vfr', frame_pattern,
        '-f', 'null', '-'
    ]
    # Capture stderr for showinfo output
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    # Parse showinfo output for pts_time and match to frames
    timestamps = [0.0]  # Start with timestamp 0.0 for the first frame
    for line in result.stderr.split('\n'):
        if 'showinfo' in line and 'pts_time:' in line:
            match = re.search(r'pts_time:([0-9.]+)', line)
            if match:
                timestamps.append(float(match.group(1)))
    
    # List the extracted frames in order
    frames = sorted([os.path.join(out_dir, f) for f in os.listdir(out_dir) if f.startswith('cut_') and f.endswith('.jpg')])
    
    # Ensure we have the same number of timestamps and frames
    if len(timestamps) != len(frames):
        print(f"Warning: Number of timestamps ({len(timestamps)}) doesn't match number of frames ({len(frames)})")
        # Use the shorter length to avoid index errors
        min_len = min(len(timestamps), len(frames))
        timestamps = timestamps[:min_len]
        frames = frames[:min_len]
    
    # Pair timestamps with frames
    return list(zip(timestamps, frames))

def transcribe_audio(audio_path: str, model_size: str = 'base') -> List[dict]:
    """
    Transcribe audio using OpenAI Whisper. Returns a list of segments (start, end, text).
    """
    model = whisper.load_model(model_size)
    result = model.transcribe(audio_path)
    segments = [
        {'start': seg['start'], 'end': seg['end'], 'text': seg['text']}
        for seg in result['segments']
    ]
    return segments

def group_transcript_by_cuts(transcript: List[dict], cuts: List[float]) -> List[List[dict]]:
    """
    Group transcript segments by cut intervals.
    Returns a list of groups, each group is a list of segments within a cut interval.
    """
    if not cuts:
        return [transcript]
    groups = []
    cut_points = cuts + [float('inf')]
    seg_idx = 0
    for i in range(len(cut_points) - 1):
        group = []
        while seg_idx < len(transcript) and cut_points[i] <= transcript[seg_idx]['start'] < cut_points[i+1]:
            group.append(transcript[seg_idx])
            seg_idx += 1
        groups.append(group)
    return groups

def ensure_temp_dir():
    temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir

def download_media_and_metadata(url: str) -> Dict:
    """
    Download media (video/images) from YouTube, TikTok, or Instagram (no login required).
    Extract tags and, if possible, description/caption for each post.
    Save all temp files to app/temp/ for inspection.
    Returns a dict with: files, tags, description, source, temp_dir
    """
    temp_dir = os.path.join(ensure_temp_dir(), str(uuid.uuid4()))
    os.makedirs(temp_dir, exist_ok=True)
    url_l = url.lower()
    files, tags, description, source = [], [], '', 'unknown'

    if any(d in url_l for d in ('youtube.com', 'youtu.be', 'tiktok.com')):
        source = 'youtube/tiktok'
        opts = {
            'outtmpl': os.path.join(temp_dir, '%(id)s.%(ext)s'),
            'format': 'bestvideo+bestaudio/best',
            'quiet': True,
            'noplaylist': True
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            tags = info.get('tags', []) or []
            description = info.get('description', '')
        files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.lower().endswith(('.mp4', '.mkv', '.webm', '.jpg', '.jpeg', '.png'))]

    elif 'instagram.com' in url_l:
        source = 'instagram'
        # Remove any query parameters and trailing slashes
        clean_url = url.split('?')[0].rstrip('/')
        try:
            # First try with instaloader
            L = instaloader.Instaloader(
                dirname_pattern=temp_dir,
                download_videos=True,
                download_video_thumbnails=True,
                download_geotags=False,
                download_comments=False,
                save_metadata=False,
                post_metadata_txt_pattern=''
            )
            
            # Get the post
            shortcode = clean_url.split('/')[-1]
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            description = post.caption or ''
            tags = [t.strip('#') for t in (post.caption or '').split() if t.startswith('#')]
            
            # Download the post
            L.download_post(post, target=temp_dir)
            
            # Get all downloaded files
            files = []
            for root, _, filenames in os.walk(temp_dir):
                for filename in filenames:
                    if filename.lower().endswith(('.mp4', '.mkv', '.webm', '.jpg', '.jpeg', '.png')):
                        files.append(os.path.join(root, filename))
            
            if not files:
                print("Warning: No files downloaded with instaloader, trying fallback method...")
                # Fallback to direct download if instaloader fails
                os.system(f"instaloader --dirname-pattern={temp_dir} --no-metadata-json {clean_url}")
                files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) 
                        if f.lower().endswith(('.mp4', '.mkv', '.webm', '.jpg', '.jpeg', '.png'))]
                
        except Exception as e:
            print(f"Warning: Could not fetch metadata: {e}. Trying to download media anyway...")
            os.system(f"instaloader --dirname-pattern={temp_dir} --no-metadata-json {clean_url}")
            files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) 
                    if f.lower().endswith(('.mp4', '.mkv', '.webm', '.jpg', '.jpeg', '.png'))]
    else:
        raise ValueError('Unsupported URL')

    return {
        'files': files,
        'tags': tags,
        'description': description,
        'source': source,
        'temp_dir': temp_dir,
        'link': url
    }

def get_video_duration(video_path: str) -> float:
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return float(result.stdout.strip())
    except Exception:
        return None

def process_video(video_file: str, temp_dir: str, threshold: float = DEFAULT_SCENE_THRESHOLD) -> dict:
    """
    Process a single video file consistently, whether it's from a carousel or standalone.
    Returns a dict with scenes, transcript, and OCR results.
    """
    print(f"\nProcessing video: {video_file}")
    scenes = []
    transcript_segments = []
    ocr_results = []
    
    try:
        # Get transcript
        transcript = transcribe_audio(video_file)
        transcript_segments.extend(transcript)
        
        # Extract frames and scene cuts
        frames_dir = os.path.join(temp_dir, 'frames', os.path.basename(video_file))
        scene_cuts = extract_scene_cuts_and_frames(video_file, frames_dir, threshold=threshold)
        print('Scene cuts:', [t for t, _ in scene_cuts])
        print('Transcript segments:', transcript)
        print('Extracted frames:', [frame for _, frame in scene_cuts])
        
        # Get video duration
        duration = get_video_duration(video_file)
        
        # Process each scene
        for i, (start, frame_path) in enumerate(scene_cuts):
            end = scene_cuts[i+1][0] if i+1 < len(scene_cuts) else duration
            scene_transcript = [
                seg['text'] for seg in transcript
                if not (seg['end'] <= start or (end is not None and seg['start'] >= end))
            ]
            onscreen_text = ocr_image(frame_path) if frame_path else ''
            scenes.append({
                'start': start,
                'end': end,
                'transcript': scene_transcript,
                'onscreenText': onscreen_text,
                'source': video_file
            })
            if frame_path:
                ocr_results.append({'frame': frame_path, 'ocr': onscreen_text})
                
        return {
            'scenes': scenes,
            'transcript': transcript_segments,
            'ocr_results': ocr_results
        }
    except Exception as e:
        print(f"Error processing video {video_file}: {e}")
        return {
            'scenes': [],
            'transcript': [],
            'ocr_results': []
        }


def extract_and_downscale_scene(input_video, start, end, output_path, target_width=480):
    import subprocess
    cmd = [
        'ffmpeg', '-y', '-i', input_video,
        '-ss', str(start),
        '-to', str(end),
        '-vf', f'scale={target_width}:-2',
        '-c:v', 'libx264',  # Use H.264 codec for MP4
        '-crf', '24',  # Lower CRF for better quality (23-28 is good range)
        '-preset', 'medium',  # Balance between speed and compression
        '-movflags', '+faststart',  # Enable streaming
        '-an',  # remove audio for smaller size
        output_path
    ]
    subprocess.run(cmd, check=True)

def cleanup_temp_files(temp_dir: str):
    """
    Clean up temporary files, keeping only result.json and scene videos.
    """
    print("\nCleaning up temporary files...")
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            file_path = os.path.join(root, file)
            # Keep result.json and scene videos
            if file == 'result.json' or '_scene' in file and file.endswith('.mp4'):
                continue
            try:
                os.remove(file_path)
                print(f"Removed: {file_path}")
            except Exception as e:
                print(f"Could not remove {file_path}: {e}")
        
        # Remove empty directories
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            try:
                os.rmdir(dir_path)
                print(f"Removed empty directory: {dir_path}")
            except Exception:
                pass  # Directory not empty, skip it

# Enhanced CLI harness for full pipeline
if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: python media_utils.py <url> [threshold]')
        sys.exit(1)
    if len(sys.argv) > 2:
        threshold = float(sys.argv[2])
    else:
        threshold = DEFAULT_SCENE_THRESHOLD

    # First download all media
    result = download_media_and_metadata(sys.argv[1])
    print(result)
    
    # Group files by type and pair videos with their thumbnails
    video_files = [f for f in result['files'] if f.lower().endswith(('.mp4', '.mkv', '.webm'))]
    image_files = [f for f in result['files'] if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    # Create a mapping of video files to their thumbnails
    video_thumbnails = {}
    for video in video_files:
        base_name = os.path.splitext(video)[0]
        for img in image_files:
            if img.startswith(base_name):
                video_thumbnails[video] = img
                break
    
    print(f"\nFound {len(video_files)} videos and {len(image_files)} images")
    
    # Process all videos consistently
    videos_output = []
    all_ocr_results = []
    all_transcript_segments = []
    
    for video_file in video_files:
        print(f"\nProcessing video: {video_file}")
        video_scenes = []
        video_ocr_results = []
        video_transcript_segments = []
        try:
            video_name = os.path.splitext(os.path.basename(video_file))[0]
            frames_dir = os.path.join(result['temp_dir'], 'frames', video_name)
            os.makedirs(frames_dir, exist_ok=True)
            thumbnail = None
            for img in image_files:
                if img.startswith(video_name):
                    thumbnail = img
                    break
            try:
                transcript = transcribe_audio(video_file)
                video_transcript_segments.extend(transcript)
            except Exception as e:
                print(f"Warning: Could not transcribe video {video_file}: {e}")
                transcript = []
            try:
                scene_cuts = extract_scene_cuts_and_frames(video_file, frames_dir, threshold=threshold)
                print('Scene cuts:', [t for t, _ in scene_cuts])
                print('Extracted frames:', [frame for _, frame in scene_cuts])
            except Exception as e:
                print(f"Warning: Could not extract scenes from video {video_file}: {e}")
                scene_cuts = []
            duration = get_video_duration(video_file)
            if not scene_cuts and thumbnail:
                onscreen_text = ocr_image(thumbnail)
                video_scenes.append({
                    'start': 0,
                    'end': duration if duration else 0,
                    'transcript': [],
                    'onscreenText': onscreen_text,
                    'thumbnail': thumbnail
                })
                video_ocr_results.append({'frame': thumbnail, 'ocr': onscreen_text})
            else:
                for i, (start, frame_path) in enumerate(scene_cuts):
                    end = scene_cuts[i+1][0] if i+1 < len(scene_cuts) else duration
                    scene_transcript = [
                        seg['text'] for seg in transcript
                        if not (seg['end'] <= start or (end is not None and seg['start'] >= end))
                    ]
                    onscreen_text = ocr_image(frame_path) if frame_path else ''
                    video_scenes.append({
                        'start': start,
                        'end': end,
                        'transcript': scene_transcript,
                        'onscreenText': onscreen_text
                    })
                    if frame_path:
                        video_ocr_results.append({'frame': frame_path, 'ocr': onscreen_text})
        except Exception as e:
            print(f"Error processing video {video_file}: {e}")
        videos_output.append({
            'video': video_file,
            'scenes': video_scenes,
            'transcript': video_transcript_segments,
            'ocr': video_ocr_results
        })
        all_ocr_results.extend(video_ocr_results)
        all_transcript_segments.extend(video_transcript_segments)
    
    # Process remaining images (those not used as video thumbnails)
    used_thumbnails = set(video_thumbnails.values())
    remaining_images = [img for img in image_files if img not in used_thumbnails]
    images = []
    for image_file in remaining_images:
        print(f"\nProcessing image: {image_file}")
        try:
            ocr_text = ocr_image(image_file, reader=EASYOCR_READER)
            images.append({
                'link': result['link'],
                'text': ocr_text,
                'source': image_file
            })
            all_ocr_results.append({'image': image_file, 'ocr': ocr_text})
        except Exception as e:
            print(f"Error processing image {image_file}: {e}")
    
    # After all processing, downscale and store file references
    videos_output_with_scene_files = []
    for video_entry in videos_output:
        video_path = video_entry['video']
        scenes = video_entry['scenes']
        for idx, scene in enumerate(scenes):
            start = scene['start']
            end = scene['end']
            scene_file_small = video_path.replace('.mp4', f'_scene{idx+1}.mp4').replace('.mkv', f'_scene{idx+1}.mkv').replace('.webm', f'_scene{idx+1}.webm')
            try:
                extract_and_downscale_scene(video_path, start, end, scene_file_small, target_width=480)
            except Exception as e:
                print(f"Warning: Could not extract/downscale scene {idx+1} from {video_path}: {e}")
                scene_file_small = None
            scene['scene_file_small'] = scene_file_small
        # Keep only scenes and add link with carousel index if applicable
        video_entry = {
            'scenes': video_entry['scenes'],
            'link': result['link'].split('?')[0].rstrip('/') + ('?img_index=' + video_path.split('_')[-1].split('.')[0] if '_UTC_' in video_path else '')
        }
        videos_output_with_scene_files.append(video_entry)

    # Save the structured result to temp_dir/result.json
    output = {
        'link': result['link'],
        'tags': result['tags'],
        'description': result['description'],
        'source': result['source'],
        'videos': videos_output_with_scene_files,
        'images': images,
        'media_count': {
            'videos': len(video_files),
            'images': len(remaining_images)
        }
    }
    # NOTE: Once you trust the output JSON, you can safely delete all files in temp_dir except:
    #   - result.json (and optionally transcript.json, scenes.json, ocr.json for debugging)
    #   - *_scene*_small.mp4 files for each scene you want to keep
    # All other original and intermediate files can be deleted for storage efficiency.
    
    # Save all results with proper organization
    with open(os.path.join(result['temp_dir'], 'result.json'), 'w') as f:
        json.dump(output, f, indent=2)
    with open(os.path.join(result['temp_dir'], 'transcript.json'), 'w') as f:
        json.dump(all_transcript_segments, f, indent=2)
    with open(os.path.join(result['temp_dir'], 'scenes.json'), 'w') as f:
        json.dump(videos_output_with_scene_files, f, indent=2)
    with open(os.path.join(result['temp_dir'], 'ocr.json'), 'w') as f:
        json.dump(all_ocr_results, f, indent=2)
    
    print(f"\nSaved result to {os.path.join(result['temp_dir'], 'result.json')}")
    print(f"Saved transcript to {os.path.join(result['temp_dir'], 'transcript.json')}")
    print(f"Saved scenes to {os.path.join(result['temp_dir'], 'scenes.json')}")
    print(f"Saved ocr to {os.path.join(result['temp_dir'], 'ocr.json')}")
    
    # Clean up temporary files
    cleanup_temp_files(result['temp_dir']) 