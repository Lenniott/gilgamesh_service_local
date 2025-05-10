import os
import uuid
import instaloader
import yt_dlp

def ensure_temp_dir():
    import os
    temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir

def download_media_and_metadata(url: str) -> dict:
    temp_dir = os.path.join(ensure_temp_dir(), str(uuid.uuid4()))
    os.makedirs(temp_dir, exist_ok=True)
    url_l = url.lower()
    files, tags, description, source = [], [], '', 'unknown'

    if any(d in url_l for d in ('youtube.com', 'youtu.be', 'tiktok.com')):
        source = 'youtube/tiktok'
        opts = {
            'outtmpl': os.path.join(temp_dir, '%(id)s.%(ext)s'),
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
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
        clean_url = url.split('?')[0].rstrip('/')
        try:
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
            files = []
            for root, _, filenames in os.walk(temp_dir):
                for filename in filenames:
                    if filename.lower().endswith(('.mp4', '.mkv', '.webm', '.jpg', '.jpeg', '.png')):
                        files.append(os.path.join(root, filename))
            if not files:
                os.system(f"instaloader --dirname-pattern={temp_dir} --no-metadata-json {clean_url}")
                files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.lower().endswith(('.mp4', '.mkv', '.webm', '.jpg', '.jpeg', '.png'))]
        except Exception as e:
            os.system(f"instaloader --dirname-pattern={temp_dir} --no-metadata-json {clean_url}")
            files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.lower().endswith(('.mp4', '.mkv', '.webm', '.jpg', '.jpeg', '.png'))]
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
