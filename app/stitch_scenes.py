#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import base64
import tempfile
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class SceneInput:
    video: str  # base64 string
    video_id: str  # video identifier for debugging
    audio: str = None  # base64 string or None
    show_debug: bool = False  # whether to show debug overlay

def get_video_duration(video_path: str) -> float:
    """Get the duration of a video file in seconds."""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration_str = result.stdout.strip()
        if not duration_str:
            raise ValueError(f"No duration found for video: {video_path}")
        duration = float(duration_str)
        if duration <= 0:
            raise ValueError(f"Invalid duration for video: {duration}")
        return duration
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Failed to get video duration for {video_path}: {e.stderr}")
    except ValueError as e:
        raise ValueError(f"Invalid duration data for video {video_path}: {e}")

def get_audio_duration(audio_path: str) -> float:
    """Get the duration of an audio file in seconds."""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        audio_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration_str = result.stdout.strip()
        if not duration_str:
            raise ValueError(f"No duration found for audio: {audio_path}")
        duration = float(duration_str)
        if duration <= 0:
            raise ValueError(f"Invalid duration for audio: {duration}")
        return duration
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Failed to get audio duration for {audio_path}: {e.stderr}")
    except ValueError as e:
        raise ValueError(f"Invalid duration data for audio {audio_path}: {e}")

def loop_video(input_path: str, target_duration: float, output_path: str):
    """Loop a video to match the target duration."""
    video_duration = get_video_duration(input_path)
    
    # Handle case where video has no duration (avoid division by zero)
    if video_duration <= 0:
        raise ValueError(f"Video has invalid duration: {video_duration}")
    
    if video_duration >= target_duration:
        # If video is longer, just trim it
        cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-t', str(target_duration),
            '-c', 'copy',
            output_path
        ]
    else:
        # Calculate number of loops needed
        loops = int(target_duration / video_duration) + 1
        
        # Create a concat file for looping
        concat_file = os.path.join(os.path.dirname(output_path), 'concat.txt')
        with open(concat_file, 'w') as f:
            for _ in range(loops):
                f.write(f"file '{input_path}'\n")
        
        try:
            # Concatenate the video
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-t', str(target_duration),  # Trim to exact duration
                '-c', 'copy',
                output_path
            ]
            subprocess.run(cmd, check=True)
        finally:
            if os.path.exists(concat_file):
                os.unlink(concat_file)

def decode_base64_to_tempfile(base64_str: str, extension: str = '.mp4') -> str:
    """Decode a base64 string to a temporary file and return its path."""
    temp_file = tempfile.NamedTemporaryFile(suffix=extension, delete=False)
    temp_path = temp_file.name
    
    try:
        video_bytes = base64.b64decode(base64_str)
        with open(temp_path, 'wb') as f:
            f.write(video_bytes)
        return temp_path
    except Exception as e:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise e

def combine_video_audio(video_path: str, audio_path: str, output_path: str):
    """Combine video and audio files - AUDIO IS KING! Loop video to match audio duration."""
    try:
        # Get durations
        video_duration = get_video_duration(video_path)
        audio_duration = get_audio_duration(audio_path)
        
        # AUDIO IS KING - video must match audio duration
        target_duration = audio_duration
        
        if video_duration < audio_duration:
            # Need to loop the video to match audio length
            print(f"Looping video ({video_duration:.1f}s) to match audio ({audio_duration:.1f}s)")
            
            # Create looped video first
            looped_video_path = output_path.replace('.mp4', '_looped.mp4')
            loop_video(video_path, audio_duration, looped_video_path)
            
            # Then combine with audio
            cmd = [
                'ffmpeg', '-y',
                '-i', looped_video_path,
                '-i', audio_path,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-map', '0:v:0',  # Video from first input (looped)
                '-map', '1:a:0',  # Audio from second input
                '-shortest',      # Stop when shortest stream ends (should be same length)
                output_path
            ]
            subprocess.run(cmd, check=True)
            
            # Clean up temp looped video
            if os.path.exists(looped_video_path):
                os.unlink(looped_video_path)
                
        else:
            # Video is longer than audio - cut video to match audio
            print(f"Cutting video ({video_duration:.1f}s) to match audio ({audio_duration:.1f}s)")
            
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-i', audio_path,
                '-t', str(audio_duration),  # Cut to audio duration
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-map', '0:v:0',  # Video from first input
                '-map', '1:a:0',  # Audio from second input
                output_path
            ]
            subprocess.run(cmd, check=True)
        
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Failed to combine video and audio: {e}")

def add_debug_overlay(input_path: str, output_path: str, video_id: str):
    """Add a debug overlay showing the video ID."""
    cmd = [
        'ffmpeg', '-y',
        '-i', input_path,
        '-vf', f"drawtext=text='{video_id}':x=10:y=10:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.5",
        '-c:a', 'copy',
        output_path
    ]
    subprocess.run(cmd, check=True)

def process_scene(scene: SceneInput, temp_dir: str, scene_index: int) -> str:
    """Process a single scene, handling video looping and audio sync."""
    temp_files = []
    
    # Save video to temp file
    video_path = os.path.join(temp_dir, f"scene_{scene_index}_video.mp4")
    with open(video_path, "wb") as f:
        f.write(base64.b64decode(scene.video))
    temp_files.append(video_path)
    
    # Add debug overlay if requested
    if scene.show_debug:
        debug_path = os.path.join(temp_dir, f"scene_{scene_index}_debug.mp4")
        add_debug_overlay(video_path, debug_path, scene.video_id)
        video_path = debug_path
        temp_files.append(debug_path)
    
    # Process audio if present
    if scene.audio:
        audio_path = os.path.join(temp_dir, f"scene_{scene_index}_audio.mp3")
        with open(audio_path, "wb") as f:
            f.write(base64.b64decode(scene.audio))
        temp_files.append(audio_path)
        
        # Combine video and audio
        output_path = os.path.join(temp_dir, f"scene_{scene_index}_combined.mp4")
        combine_video_audio(video_path, audio_path, output_path)
        temp_files.append(output_path)
        return output_path
    
    return video_path

def stitch_scenes_to_base64(scenes: List[SceneInput]) -> str:
    """
    Stitch together scenes from base64 strings and return as base64.
    Handles video looping and audio sync.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Process each scene
            scene_files = []
            print(f"Processing {len(scenes)} scenes...")
            
            for i, scene in enumerate(scenes):
                print(f"Processing scene {i+1}/{len(scenes)}")
                scene_file = process_scene(scene, temp_dir, i)  # Pass scene index
                scene_files.append(scene_file)
                print(f"Scene {i+1} processed: {scene_file}")
            
            if not scene_files:
                raise ValueError("No valid scenes to process")
            
            # Create concat file
            concat_file = os.path.join(temp_dir, 'concat.txt')
            with open(concat_file, 'w') as f:
                for scene in scene_files:
                    f.write(f"file '{scene}'\n")
            
            # Debug: Print concat file contents
            print("\nConcat file contents:")
            with open(concat_file, 'r') as f:
                print(f.read())
            
            # Final output path
            output_path = os.path.join(temp_dir, 'final.mp4')
            
            # Concatenate all scenes
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',
                output_path
            ]
            print(f"\nRunning ffmpeg command: {' '.join(cmd)}")  # Debug log
            subprocess.run(cmd, check=True)
            
            # Read the final file and convert to base64
            with open(output_path, 'rb') as f:
                video_bytes = f.read()
                return base64.b64encode(video_bytes).decode('utf-8')
                
        except Exception as e:
            print(f"Error in stitch_scenes_to_base64: {e}")
            raise

def stitch_scenes_from_json(json_path: str) -> str:
    """Stitch scenes from a JSON file and return as base64."""
    with open(json_path, 'r') as f:
        scenes_data = json.load(f)
    
    scenes = [SceneInput(**scene) for scene in scenes_data]
    return stitch_scenes_to_base64(scenes)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python stitch_scenes.py <input.json>")
        sys.exit(1)
    
    json_path = sys.argv[1]
    
    base64_video = stitch_scenes_from_json(json_path)
    print(f"Stitched video as base64: {base64_video}") 