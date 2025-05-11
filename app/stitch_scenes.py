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
    audio: str = None  # base64 string or None

def get_video_duration(video_path: str) -> float:
    """Get the duration of a video file in seconds."""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())

def get_audio_duration(audio_path: str) -> float:
    """Get the duration of an audio file in seconds."""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        audio_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())

def loop_video(input_path: str, target_duration: float, output_path: str):
    """Loop a video to match the target duration."""
    video_duration = get_video_duration(input_path)
    
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

def process_scene(scene: SceneInput, temp_dir: str, scene_index: int) -> str:
    """Process a single scene, handling video looping and audio sync."""
    temp_files = []
    try:
        # Decode video
        video_path = decode_base64_to_tempfile(scene.video, '.mp4')
        temp_files.append(video_path)
        
        if scene.audio:
            # Decode audio
            audio_path = decode_base64_to_tempfile(scene.audio, '.mp3')
            temp_files.append(audio_path)
            
            # Get durations
            audio_duration = get_audio_duration(audio_path)
            video_duration = get_video_duration(video_path)
            
            # Determine target duration
            target_duration = max(audio_duration, 5.0)  # At least 5 seconds
            
            # Loop video if needed
            if video_duration < target_duration:
                looped_video = os.path.join(temp_dir, f'looped_{scene_index}.mp4')
                loop_video(video_path, target_duration, looped_video)
                temp_files.append(looped_video)
                video_path = looped_video
            
            # Combine video and audio
            output_path = os.path.join(temp_dir, f'combined_{scene_index}.mp4')
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-i', audio_path,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-shortest',  # Match to shortest stream
                output_path
            ]
            subprocess.run(cmd, check=True)
            temp_files.append(output_path)
            return output_path
        else:
            # No audio, just ensure video is at least 5 seconds
            video_duration = get_video_duration(video_path)
            if video_duration < 5.0:
                output_path = os.path.join(temp_dir, f'looped_{scene_index}.mp4')
                loop_video(video_path, 5.0, output_path)
                temp_files.append(output_path)
                return output_path
            return video_path
            
    finally:
        # Clean up intermediate files
        for temp_file in temp_files[:-1]:  # Keep the last file (the output)
            if os.path.exists(temp_file):
                os.unlink(temp_file)

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