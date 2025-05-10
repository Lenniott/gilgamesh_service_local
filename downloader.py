import os
import sys
import uuid
import shutil
import subprocess
import json
from typing import List, Dict
import yt_dlp
import instaloader
import whisper
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import re
import unicodedata


def get_frame_rate(video_path: str) -> float:
    """
    Get frame rate of a video using ffprobe.
    """
    cmd = [
        'ffprobe', '-v', '0', '-of', 'csv=p=0',
        '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate', video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    num, denom = map(int, result.stdout.decode().strip().split('/'))
    return num / denom


def extract_frames(video_path: str, out_dir: str, interval: int):
    """
    Extract one frame every `interval` seconds into out_dir.
    """
    os.makedirs(out_dir, exist_ok=True)
    subprocess.run([
        'ffmpeg', '-i', video_path,
        '-vf', f'fps=1/{interval}',
        os.path.join(out_dir, 'frame_%06d.png')
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def preprocess_image(image_path: str) -> Image.Image:
    """
    Enhance image for better OCR results.
    """
    image = Image.open(image_path).convert('L')  # convert to grayscale
    image = image.filter(ImageFilter.MedianFilter())
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2)  # increase contrast
    return image


def ocr_extract_segments(frames_dir: str, interval: int) -> List[Dict]:
    """
    Run OCR on extracted frames and group unchanged text into segments.
    """
    files = sorted(f for f in os.listdir(frames_dir) if f.startswith('frame_'))
    segments = []
    prev_text = None
    seg_start = 0.0

    for idx, fname in enumerate(files):
        timestamp = idx * interval
        path = os.path.join(frames_dir, fname)
        try:
            image = preprocess_image(path)
            text = clean_text(pytesseract.image_to_string(image).strip())
        except Exception:
            text = ''

        if prev_text is None:
            prev_text, seg_start = text, timestamp
        elif text != prev_text:
            segments.append({'start': seg_start, 'end': timestamp, 'text': prev_text})
            prev_text, seg_start = text, timestamp

    if prev_text is not None:
        segments.append({'start': seg_start, 'end': timestamp + interval, 'text': prev_text})

    return segments


def merge_transcripts(audio: List[Dict], ocr: List[Dict]) -> List[Dict]:
    """
    Merge audio and OCR segments by matching overlapping timestamps.
    """
    merged = []
    for a in audio:
        match = next((o for o in ocr if o['start'] <= a['start'] < o['end']), None)
        merged.append({
            'start': a['start'],
            'end': a['end'],
            'audio_text': a['text'],
            'image_text': match['text'] if match else ''
        })
    return merged


def process_video(path: str, temp_folder: str, interval: int = 2) -> Dict:
    """
    Handle video: transcribe audio, extract OCR segments, merge, and return structured data.
    """
    audio_path = os.path.join(temp_folder, 'audio.wav')
    subprocess.run([
        'ffmpeg', '-i', path, '-vn', '-acodec', 'pcm_s16le',
        '-ar', '16000', '-ac', '1', audio_path
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    model = whisper.load_model('base')
    result = model.transcribe(audio_path)
    audio_segments = [{'start': seg['start'], 'end': seg['end'], 'text': clean_text(seg['text'])} for seg in result['segments']]

    frames_dir = os.path.join(temp_folder, 'frames')
    extract_frames(path, frames_dir, interval)
    ocr_segments = ocr_extract_segments(frames_dir, interval)

    merged = merge_transcripts(audio_segments, ocr_segments)

    return {
        'type': 'video',
        'frame_rate': get_frame_rate(path),
        'audio_segments': audio_segments,
        'ocr_segments': ocr_segments,
        'merged_segments': merged
    }


def process_image(path: str) -> Dict:
    """
    Handle image: run OCR and return text.
    """
    try:
        image = preprocess_image(path)
        text = clean_text(pytesseract.image_to_string(image).strip())
    except Exception as e:
        text = f'[OCR error: {e}]'
    return {'type': 'image', 'text': text}


def download_media(url: str, temp_folder: str) -> Dict:
    """
    Download media from URL into temp_folder and return list of file paths plus tags/source.
    """
    url_l = url.lower()
    files, tags, source = [], [], 'unknown'

    if any(d in url_l for d in ('youtube.com', 'youtu.be', 'tiktok.com')):
        source = 'youtube/tiktok'
        opts = {
            'outtmpl': os.path.join(temp_folder, '%(id)s.%(ext)s'),
            'format': 'bestvideo+bestaudio',
            'quiet': True,
            'noplaylist': True
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            tags = info.get('tags', []) or []
            description = info.get('description', '')
        files = [os.path.join(temp_folder, f) for f in os.listdir(temp_folder) if f.lower().endswith(('.mp4', '.mkv', '.webm', '.jpg', '.jpeg', '.png'))]

    elif 'instagram.com' in url_l:
        source = 'instagram'
        L = instaloader.Instaloader(dirname_pattern=temp_folder, download_videos=True, save_metadata=False)
        shortcode = url.rstrip('/').split('/')[-1]
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        description = post.caption or ''
        tags = [t.strip('#') for t in (post.caption or '').split() if t.startswith('#')]
        L.download_post(post, target=temp_folder)
        files = [os.path.join(temp_folder, f) for f in os.listdir(temp_folder) if f.lower().endswith(('.mp4', '.mkv', '.webm', '.jpg', '.jpeg', '.png'))]

    else:
        raise ValueError('Unsupported URL')

    return {'files': files, 'tags': tags, 'source': source, 'description': description}


def main(urls: List[str]):
    results = []
    for url in urls:
        temp = f"/tmp/{uuid.uuid4()}"
        os.makedirs(temp, exist_ok=True)
        try:
            info = download_media(url, temp)
            media_data = []
            for path in info['files']:
                if path.lower().endswith(('.mp4', '.mkv', '.webm')):
                    media_data.append(process_video(path, temp))
                elif path.lower().endswith(('.jpg', '.jpeg', '.png')):
                    media_data.append(process_image(path))
            results.append({
                'url': url,
                'source': info['source'],
                'tags': info['tags'],
                'media': media_data
            })
        finally:
            shutil.rmtree(temp)

    print(json.dumps(results, indent=2))


def clean_text(text: str) -> str:
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python script.py <url1> <url2> ...')
        sys.exit(1)
    main(sys.argv[1:])
