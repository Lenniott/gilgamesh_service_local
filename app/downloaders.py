import os
import uuid
import asyncio
import instaloader
import yt_dlp
from typing import Dict, List, Optional

async def ensure_temp_dir() -> str:
    """Ensure temp directory exists and return its path."""
    temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
    await asyncio.to_thread(os.makedirs, temp_dir, exist_ok=True)
    return temp_dir

async def download_youtube(url: str, temp_dir: str) -> Dict:
    """Download YouTube/TikTok content asynchronously."""
    files, tags, description = [], [], ''

    opts = {
        'outtmpl': os.path.join(temp_dir, '%(id)s.%(ext)s'),
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'quiet': True,
        'noplaylist': True
    }

    def _download():
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return info.get('tags', []) or [], info.get('description', '')

    # Run yt-dlp in a thread since it's blocking
    tags, description = await asyncio.to_thread(_download)

    # List files in temp directory
    files = await asyncio.to_thread(
        lambda: [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) 
                if f.lower().endswith(('.mp4', '.mkv', '.webm', '.jpg', '.jpeg', '.png'))]
    )

    return {
        'files': files,
        'tags': tags,
        'description': description,
        'source': 'youtube/tiktok'
    }

async def download_instagram(url: str, temp_dir: str) -> Dict:
    """Download Instagram content asynchronously."""
    files, tags, description = [], [], ''
    clean_url = url.split('?')[0].rstrip('/')

    def _download():
        L = instaloader.Instaloader(
            dirname_pattern=temp_dir,
            download_videos=True,
            download_video_thumbnails=True,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            post_metadata_txt_pattern=''
        )
        shortcode = clean_url.split('/')[-1]
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        description = post.caption or ''
        tags = [t.strip('#') for t in (post.caption or '').split() if t.startswith('#')]
        L.download_post(post, target=temp_dir)
        return tags, description

    try:
        # Run instaloader in a thread since it's blocking
        tags, description = await asyncio.to_thread(_download)

        # List files in temp directory
        def _list_files():
            result = []
            for root, _, filenames in os.walk(temp_dir):
                for filename in filenames:
                    if filename.lower().endswith(('.mp4', '.mkv', '.webm', '.jpg', '.jpeg', '.png')):
                        result.append(os.path.join(root, filename))
            return result

        files = await asyncio.to_thread(_list_files)

        if not files:
            # Fallback to command line instaloader
            await asyncio.to_thread(
                lambda: os.system(f"instaloader --dirname-pattern={temp_dir} --no-metadata-json {clean_url}")
            )
            files = await asyncio.to_thread(
                lambda: [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) 
                        if f.lower().endswith(('.mp4', '.mkv', '.webm', '.jpg', '.jpeg', '.png'))]
            )

    except Exception as e:
        # Fallback to command line instaloader
        await asyncio.to_thread(
            lambda: os.system(f"instaloader --dirname-pattern={temp_dir} --no-metadata-json {clean_url}")
        )
        files = await asyncio.to_thread(
            lambda: [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) 
                    if f.lower().endswith(('.mp4', '.mkv', '.webm', '.jpg', '.jpeg', '.png'))]
        )

    return {
        'files': files,
        'tags': tags,
        'description': description,
        'source': 'instagram'
    }

async def download_media_and_metadata(url: str) -> Dict:
    """
    Download media and metadata from a URL asynchronously.
    
    Args:
        url: The URL to download from
        
    Returns:
        Dict containing:
        {
            'files': List[str],  # List of downloaded file paths
            'tags': List[str],   # List of tags
            'description': str,  # Content description
            'source': str,       # Source platform
            'temp_dir': str,     # Temporary directory path
            'link': str         # Original URL
        }
        
    Raises:
        ValueError: If URL is not supported
    """
    temp_dir = os.path.join(await ensure_temp_dir(), str(uuid.uuid4()))
    await asyncio.to_thread(os.makedirs, temp_dir, exist_ok=True)
    url_l = url.lower()
    
    if any(d in url_l for d in ('youtube.com', 'youtu.be', 'tiktok.com')):
        result = await download_youtube(url, temp_dir)
    elif 'instagram.com' in url_l:
        result = await download_instagram(url, temp_dir)
    else:
        raise ValueError('Unsupported URL')
    
    result['temp_dir'] = temp_dir
    result['link'] = url
    return result 