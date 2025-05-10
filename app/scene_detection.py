import subprocess
import re
import os

def detect_scenes(video_path: str, threshold: float = 0.22):
    cmd = [
        'ffmpeg', '-i', video_path,
        '-filter_complex', f"select='gt(scene,{threshold})',showinfo",
        '-f', 'null', '-'
    ]
    result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    cut_times = []
    for line in result.stderr.split('\n'):
        if 'showinfo' in line and 'pts_time:' in line:
            match = re.search(r'pts_time:([0-9.]+)', line)
            if match:
                cut_times.append(float(match.group(1)))
    return cut_times

def extract_scene_cuts_and_frames(video_path: str, out_dir: str, threshold: float = 0.22):
    os.makedirs(out_dir, exist_ok=True)
    first_frame_path = os.path.join(out_dir, 'cut_0000.jpg')
    first_frame_cmd = [
        'ffmpeg', '-i', video_path,
        '-vf', 'select=eq(n\,0)',
        '-vframes', '1',
        first_frame_path
    ]
    subprocess.run(first_frame_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    frame_pattern = os.path.join(out_dir, 'cut_%04d.jpg')
    cmd = [
        'ffmpeg', '-i', video_path,
        '-vf', f"select='gt(scene,{threshold})',showinfo",
        '-vsync', 'vfr', frame_pattern,
        '-f', 'null', '-'
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    timestamps = [0.0]
    for line in result.stderr.split('\n'):
        if 'showinfo' in line and 'pts_time:' in line:
            match = re.search(r'pts_time:([0-9.]+)', line)
            if match:
                timestamps.append(float(match.group(1)))

    frames = sorted([os.path.join(out_dir, f) for f in os.listdir(out_dir) if f.startswith('cut_') and f.endswith('.jpg')])

    if len(timestamps) != len(frames):
        print(f"Warning: Number of timestamps ({len(timestamps)}) doesn't match number of frames ({len(frames)})")
        min_len = min(len(timestamps), len(frames))
        timestamps = timestamps[:min_len]
        frames = frames[:min_len]

    return list(zip(timestamps, frames))

def get_video_duration(video_path: str):
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return float(result.stdout.strip())
    except Exception:
        return None
