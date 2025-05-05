import os
import uuid
import shutil
import yt_dlp
import instaloader
from typing import Dict, List, Union
import base64
import subprocess
import whisper
from PIL import Image
import pytesseract

def download_media(url: str) -> dict:
    """
    Download media, extract audio, transcribe it, and return the text.
    Automatically detects source and cleans up after.
    Returns dict with 'source', 'tags', 'transcription', 'media_type'
    """
    temp_folder = f"/tmp/{uuid.uuid4()}"
    os.makedirs(temp_folder, exist_ok=True)

    url_lower = url.lower()

    try:
        if any(domain in url_lower for domain in ["youtube.com", "youtu.be", "tiktok.com"]):
            result = download_youtube(url, temp_folder)
            result["source"] = "youtube/tiktok"
            result["media_type"] = "video"
        elif "instagram.com" in url_lower:
            result = download_instagram(url, temp_folder)
            result["source"] = "instagram"
        else:
            raise ValueError("Unsupported URL format.")

        return result

    finally:
        shutil.rmtree(temp_folder)

def process_media_file(file_path: str, temp_folder: str) -> dict:
    """Process a single media file and return its transcription or text content"""
    result = {}
    
    # Check if it's a video file
    if file_path.lower().endswith(('.mp4', '.mkv', '.webm')):
        audio_path = os.path.join(temp_folder, "audio.wav")
        
        # Extract audio using ffmpeg
        subprocess.run([
            'ffmpeg', '-i', file_path,
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # PCM format
            '-ar', '16000',  # 16kHz sample rate
            '-ac', '1',  # Mono
            audio_path
        ], check=True, capture_output=True)

        # Transcribe audio using whisper
        model = whisper.load_model("base")
        transcription = model.transcribe(audio_path)
        result["transcription"] = transcription["text"]
        result["media_type"] = "video"
        
    # Check if it's an image file
    elif file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
        # Extract text from image using OCR
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        result["transcription"] = text
        result["media_type"] = "image"
    
    return result

def download_youtube(url: str, temp_folder: str) -> dict:
    ydl_opts = {
        'outtmpl': os.path.join(temp_folder, '%(title)s.%(ext)s'),
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        tags = info.get("tags", [])
        ydl.download([url])
    
    # Process the downloaded video
    video_files = [f for f in os.listdir(temp_folder) if f.endswith(('.mp4', '.mkv', '.webm'))]
    if video_files:
        video_path = os.path.join(temp_folder, video_files[0])
        result = process_media_file(video_path, temp_folder)
        result["tags"] = tags
        return result
    return {"tags": tags, "transcription": "", "media_type": "video"}

def download_instagram(url: str, temp_folder: str) -> dict:
    # Clean URL and extract shortcode
    url = url.split('?')[0]  # Remove query parameters
    if '/p/' in url:
        shortcode = url.split('/p/')[-1].split('/')[0]
    elif '/reel/' in url:
        shortcode = url.split('/reel/')[-1].split('/')[0]
    else:
        raise ValueError("Unsupported Instagram URL format")

    L = instaloader.Instaloader(
        download_comments=False,
        save_metadata=False,
        dirname_pattern=temp_folder,
        download_videos=True,
        download_video_thumbnails=False,
        download_geotags=False,
        download_pictures=True
    )
    
    try:
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        L.download_post(post, target='.')
        
        # Get hashtags from caption
        caption = post.caption or ""
        hashtags = [tag.strip('#') for tag in caption.split() if tag.startswith('#')]
        
        # Process all media files
        media_results = []
        for filename in os.listdir(temp_folder):
            if filename.endswith(('.mp4', '.mkv', '.webm', '.jpg', '.jpeg', '.png')):
                file_path = os.path.join(temp_folder, filename)
                result = process_media_file(file_path, temp_folder)
                media_results.append(result)
        
        # Combine results
        combined_result = {
            "tags": hashtags,
            "media_count": len(media_results),
            "media_type": "carousel" if len(media_results) > 1 else media_results[0]["media_type"] if media_results else "unknown",
            "transcriptions": [r.get("transcription", "") for r in media_results]
        }
        
        return combined_result
    except Exception as e:
        raise ValueError(f"Failed to process Instagram post: {str(e)}")
