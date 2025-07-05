import subprocess
import re
import os
import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
import tempfile

def detect_scenes(video_path: str, threshold: float = 0.22):
    """Basic scene detection - finds scene cuts using FFmpeg."""
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

def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds."""
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return float(result.stdout.strip())
    except Exception:
        return None

def extract_frames_from_scene(video_path: str, start_time: float, end_time: float, 
                            out_dir: str, scene_index: int, fps: int = 5) -> List[str]:
    """
    Extract frames from a specific scene segment at regular intervals.
    
    Args:
        video_path: Path to the video file
        start_time: Scene start time in seconds
        end_time: Scene end time in seconds
        out_dir: Output directory for frames
        scene_index: Scene number for file naming
        fps: Frames per second to extract (default: 5)
    
    Returns:
        List of extracted frame file paths
    """
    os.makedirs(out_dir, exist_ok=True)
    
    # Calculate duration and frame interval
    duration = end_time - start_time
    if duration <= 0:
        return []
    
    # Extract frames at specified FPS
    frame_pattern = os.path.join(out_dir, f'scene_{scene_index:03d}_frame_%04d.jpg')
    
    cmd = [
        'ffmpeg', '-y',
        '-ss', str(start_time),
        '-i', video_path,
        '-t', str(duration),
        '-vf', f'fps={fps}',
        '-q:v', '2',  # High quality
        frame_pattern
    ]
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Get list of extracted frames
    frames = []
    for f in os.listdir(out_dir):
        if f.startswith(f'scene_{scene_index:03d}_frame_') and f.endswith('.jpg'):
            frames.append(os.path.join(out_dir, f))
    
    return sorted(frames)

def calculate_frame_difference(frame1_path: str, frame2_path: str) -> float:
    """
    Calculate visual difference between two frames using structural similarity.
    
    Returns:
        Float between 0-1, where 1 means completely different
    """
    try:
        # Read images
        img1 = cv2.imread(frame1_path, cv2.IMREAD_GRAYSCALE)
        img2 = cv2.imread(frame2_path, cv2.IMREAD_GRAYSCALE)
        
        if img1 is None or img2 is None:
            return 0.0
        
        # Resize to same dimensions if needed
        h, w = min(img1.shape[0], img2.shape[0]), min(img1.shape[1], img2.shape[1])
        img1 = cv2.resize(img1, (w, h))
        img2 = cv2.resize(img2, (w, h))
        
        # Calculate mean squared error (simple but effective for movement detection)
        mse = np.mean((img1.astype(float) - img2.astype(float)) ** 2)
        
        # Normalize to 0-1 range (approximation)
        normalized_diff = min(mse / 10000.0, 1.0)
        
        return normalized_diff
        
    except Exception as e:
        print(f"Error calculating frame difference: {e}")
        return 0.0

def find_extreme_frames(frames: List[str], max_extremes: int = 4) -> List[Tuple[str, float, str]]:
    """
    Find the most visually different/extreme frames within a scene.
    
    Args:
        frames: List of frame file paths
        max_extremes: Maximum number of extreme frames to find
    
    Returns:
        List of tuples: (frame_path, difference_score, frame_type)
        frame_type can be 'start', 'peak', 'valley', 'end'
    """
    if len(frames) < 2:
        return [(frames[0], 0.0, 'single')] if frames else []
    
    # Calculate differences between consecutive frames
    differences = []
    for i in range(len(frames) - 1):
        diff = calculate_frame_difference(frames[i], frames[i + 1])
        differences.append((i, diff))
    
    # Always include first and last frames
    extreme_frames = [
        (frames[0], 0.0, 'start'),
        (frames[-1], 0.0, 'end')
    ]
    
    # Find peaks in differences (highest change points)
    if len(differences) > 0:
        # Sort by difference score
        sorted_diffs = sorted(differences, key=lambda x: x[1], reverse=True)
        
        # Take top differences (excluding first/last which we already have)
        peak_count = 0
        for frame_idx, diff_score in sorted_diffs:
            if peak_count >= max_extremes - 2:  # Reserve space for start/end
                break
            
            # Skip if too close to start or end
            if frame_idx > 0 and frame_idx < len(frames) - 1:
                frame_path = frames[frame_idx]
                frame_type = 'peak' if peak_count % 2 == 0 else 'valley'
                extreme_frames.append((frame_path, diff_score, frame_type))
                peak_count += 1
    
    # Sort by frame order (timestamp)
    extreme_frames.sort(key=lambda x: frames.index(x[0]) if x[0] in frames else 0)
    
    return extreme_frames

def extract_scene_cuts_and_extreme_frames(video_path: str, out_dir: str, threshold: float = 0.22) -> List[Dict]:
    """
    Enhanced scene detection that finds extreme frames within each scene cut.
    
    Returns:
        List of scene dictionaries containing:
        {
            'start_time': float,
            'end_time': float, 
            'extreme_frames': [
                {
                    'frame_path': str,
                    'timestamp': float,
                    'difference_score': float,
                    'frame_type': str  # 'start', 'peak', 'valley', 'end'
                }
            ]
        }
    """
    print(f"🎬 Starting enhanced scene detection for: {video_path}")
    
    # Step 1: Find scene cuts
    cut_times = detect_scenes(video_path, threshold)
    duration = get_video_duration(video_path)
    
    if not cut_times and duration:
        # If no cuts found, treat entire video as one scene
        cut_times = [0.0, duration]
    elif cut_times and duration:
        # Add video end time if not present
        if cut_times[-1] < duration - 1.0:
            cut_times.append(duration)
    
    print(f"📍 Found {len(cut_times)} scene cut points: {cut_times}")
    
    scenes = []
    
    # Step 2: Process each scene segment
    for i in range(len(cut_times) - 1):
        start_time = cut_times[i]
        end_time = cut_times[i + 1]
        
        print(f"\n🔍 Processing scene {i+1}: {start_time:.2f}s - {end_time:.2f}s")
        
        # Extract frames from this scene
        scene_frames = extract_frames_from_scene(
            video_path, start_time, end_time, out_dir, i, fps=3
        )
        
        if not scene_frames:
            print(f"⚠️  No frames extracted for scene {i+1}")
            continue
        
        print(f"📸 Extracted {len(scene_frames)} frames for analysis")
        
        # Find extreme frames within this scene
        extreme_frames_data = find_extreme_frames(scene_frames, max_extremes=4)
        
        # Convert to detailed format with timestamps
        extreme_frames = []
        for frame_path, diff_score, frame_type in extreme_frames_data:
            # Extract timestamp from frame position
            frame_idx = scene_frames.index(frame_path)
            scene_duration = end_time - start_time
            frame_timestamp = start_time + (frame_idx / (len(scene_frames) - 1)) * scene_duration
            
            extreme_frames.append({
                'frame_path': frame_path,
                'timestamp': frame_timestamp,
                'difference_score': diff_score,
                'frame_type': frame_type
            })
        
        print(f"🎯 Found {len(extreme_frames)} extreme frames:")
        for ef in extreme_frames:
            print(f"   • {ef['frame_type']}: {ef['timestamp']:.2f}s (diff: {ef['difference_score']:.3f})")
        
        scenes.append({
            'start_time': start_time,
            'end_time': end_time,
            'extreme_frames': extreme_frames
        })
    
    print(f"\n✅ Scene detection complete! Found {len(scenes)} scenes with extreme frames")
    return scenes

async def extract_scenes_with_ai_analysis(video_path: str, out_dir: str, threshold: float = 0.22, 
                                         use_ai_analysis: bool = True,
                                         transcript_data: Optional[List[Dict]] = None,
                                         existing_scenes: Optional[List[Dict]] = None) -> List[Dict]:
    """
    Complete scene detection with AI analysis and cleanup.
    
    Args:
        video_path: Path to the video file
        out_dir: Output directory for temporary frames
        threshold: Scene detection threshold
        use_ai_analysis: Whether to use GPT-4 Vision for scene analysis
        transcript_data: Optional transcript segments for enhanced context
        existing_scenes: Optional existing scene descriptions for video-level context
        
    Returns:
        List of scene dictionaries with AI analysis:
        [
            {
                "start_time": float,
                "end_time": float,
                "ai_description": str,
                "ai_tags": List[str],
                "analysis_success": bool,
                "has_transcript": bool,
                "scene_transcript": str or None,
                "has_video_context": bool
            }
        ]
    """
    from app.ai_scene_analysis import analyze_all_scenes_with_ai, cleanup_frame_images
    
    transcript_status = " with transcript" if transcript_data else ""
    print(f"🎬 Starting complete scene analysis{transcript_status} for: {os.path.basename(video_path)}")
    
    # Step 1: Enhanced scene detection with extreme frames
    scenes_data = extract_scene_cuts_and_extreme_frames(video_path, out_dir, threshold)
    
    if not scenes_data:
        print("❌ No scenes detected")
        return []
    
    # Step 2: AI analysis (if enabled)
    if use_ai_analysis:
        try:
            analyzed_scenes = await analyze_all_scenes_with_ai(scenes_data, transcript_data, existing_scenes)
        except Exception as e:
            print(f"⚠️  AI analysis failed: {e}")
            # Continue without AI analysis
            analyzed_scenes = []
            for i, scene in enumerate(scenes_data):
                analyzed_scenes.append({
                    "start_time": scene['start_time'],
                    "end_time": scene['end_time'],
                    "ai_description": "AI analysis not available",
                    "ai_tags": ["exercise", "movement", "mobility", "fitness", "training"],
                    "analysis_success": False,
                    "has_transcript": bool(transcript_data),
                    "scene_transcript": None
                })
    else:
        # Skip AI analysis
        analyzed_scenes = []
        for i, scene in enumerate(scenes_data):
            analyzed_scenes.append({
                "start_time": scene['start_time'],
                "end_time": scene['end_time'],
                "ai_description": "AI analysis disabled",
                "ai_tags": [],
                "analysis_success": False,
                "has_transcript": bool(transcript_data),
                "scene_transcript": None
            })
    
    # Step 3: Cleanup frame images
    try:
        await cleanup_frame_images(scenes_data)
    except Exception as e:
        print(f"⚠️  Frame cleanup failed: {e}")
    
    # Step 4: Return clean result (without frame paths)
    clean_scenes = []
    for scene in analyzed_scenes:
        clean_scene = {
            "start_time": scene['start_time'],
            "end_time": scene['end_time'],
            "ai_description": scene['ai_description'],
            "ai_tags": scene['ai_tags'],
            "analysis_success": scene['analysis_success']
        }
        
        # Include transcript-related fields if available
        if scene.get('has_transcript'):
            clean_scene["has_transcript"] = scene['has_transcript']
            clean_scene["scene_transcript"] = scene.get('scene_transcript')
        
        clean_scenes.append(clean_scene)
    
    success_count = sum(1 for scene in clean_scenes if scene.get('analysis_success', False))
    transcript_scenes = sum(1 for scene in clean_scenes if scene.get('has_transcript', False))
    
    print(f"✅ Complete scene analysis finished: {len(clean_scenes)} scenes")
    print(f"   📈 AI Success: {success_count}/{len(clean_scenes)} scenes")
    if transcript_data:
        print(f"   📝 With transcript context: {transcript_scenes}/{len(clean_scenes)} scenes")
    
    return clean_scenes

# Legacy function for backward compatibility
def extract_scene_cuts_and_frames(video_path: str, out_dir: str, threshold: float = 0.22):
    """
    Legacy function - now uses enhanced scene detection.
    Returns list of (timestamp, frame_path) tuples for the first extreme frame of each scene.
    """
    scenes = extract_scene_cuts_and_extreme_frames(video_path, out_dir, threshold)
    
    # Return first extreme frame from each scene for backward compatibility
    result = []
    for scene in scenes:
        if scene['extreme_frames']:
            first_frame = scene['extreme_frames'][0]
            result.append((first_frame['timestamp'], first_frame['frame_path']))
    
    return result
