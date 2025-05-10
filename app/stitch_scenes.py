#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from typing import List, Dict

def create_concat_file(scene_files: List[str], temp_dir: str) -> str:
    """Create a temporary file listing all scenes to concatenate."""
    concat_file = os.path.join(temp_dir, 'concat.txt')
    with open(concat_file, 'w') as f:
        for scene in scene_files:
            f.write(f"file '{scene}'\n")
    return concat_file

def stitch_scenes(result_json: str, scene_indices: List[int], output_path: str):
    """
    Stitch together specific scenes from result.json into a single MP4 video.
    
    Args:
        result_json: Path to the result.json file
        scene_indices: List of scene indices to include (0-based)
        output_path: Where to save the final MP4
    """
    # Load the result JSON
    with open(result_json, 'r') as f:
        result = json.load(f)
    
    # Get all scene files
    scene_files = []
    for video in result['videos']:
        for scene in video['scenes']:
            if scene['scene_file_small']:
                scene_files.append(scene['scene_file_small'])
    
    # Filter to only the requested scenes
    selected_scenes = [scene_files[i] for i in scene_indices if i < len(scene_files)]
    
    if not selected_scenes:
        print("No valid scenes selected!")
        return
    
    # Create temp directory for concat file
    temp_dir = os.path.dirname(result_json)
    os.makedirs(temp_dir, exist_ok=True)
    
    # Create concat file
    concat_file = create_concat_file(selected_scenes, temp_dir)
    
    try:
        # Use FFmpeg to concatenate the scenes
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',  # Copy streams without re-encoding
            output_path
        ]
        subprocess.run(cmd, check=True)
        print(f"Successfully created video at: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error creating video: {e}")
    finally:
        # Clean up concat file
        if os.path.exists(concat_file):
            os.remove(concat_file)

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python stitch_scenes.py <result.json> <output.mp4> <scene_index1> [scene_index2 ...]")
        sys.exit(1)
    
    result_json = sys.argv[1]
    output_path = sys.argv[2]
    scene_indices = [int(idx) for idx in sys.argv[3:]]
    
    stitch_scenes(result_json, scene_indices, output_path) 