import subprocess
import os
import base64
import tempfile

def extract_and_downscale_scene(input_video, start, end, target_width=480):
    """
    Extract a scene from a video and return it as a base64 blob.
    """
    # Create a temporary file for the scene
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
        temp_path = temp_file.name

    try:
        # Extract and downscale the scene
        cmd = [
            'ffmpeg', '-y', '-i', input_video,
            '-ss', str(start),
            '-to', str(end),
            '-vf', f'scale={target_width}:-2',
            '-c:v', 'libx264',
            '-crf', '24',
            '-preset', 'medium',
            '-movflags', '+faststart',
            '-an',
            temp_path
        ]
        subprocess.run(cmd, check=True)

        # Read the file and convert to base64
        with open(temp_path, 'rb') as f:
            video_bytes = f.read()
            base64_blob = base64.b64encode(video_bytes).decode('utf-8')
        
        return base64_blob
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

def cleanup_temp_files(temp_dir: str):
    print("\nCleaning up temporary files...")
    frames_folder = os.path.join(temp_dir, "frames")
    if os.path.exists(frames_folder):
        for root, dirs, files in os.walk(frames_folder, topdown=False):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    print(f"Removed frames file: {file_path}")
                except Exception as e:
                    print(f"Could not remove frames file {file_path}: {e}")
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                try:
                    os.rmdir(dir_path)
                    print(f"Removed frames subdir: {dir_path}")
                except Exception as e:
                    print(f"Could not remove frames subdir {dir_path}: {e}")
        try:
            os.rmdir(frames_folder)
            print(f"Removed frames folder: {frames_folder}")
        except Exception as e:
            print(f"Could not remove frames folder {frames_folder}: {e}")

    # Don't delete the video file until after blob generation
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            file_path = os.path.join(root, file)
            if file == 'result.json' or file.endswith('.mp4'):  # Preserve video files
                continue
            try:
                os.remove(file_path)
                print(f"Removed: {file_path}")
            except Exception as e:
                print(f"Could not remove {file_path}: {e}")
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            try:
                os.rmdir(dir_path)
                print(f"Removed empty directory: {dir_path}")
            except Exception as e:
                print(f"Could not remove empty directory {dir_path}: {e}")
