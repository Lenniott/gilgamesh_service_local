import os
import cv2
import numpy as np
import asyncio
import subprocess
import re
import string
import json
import base64
import tempfile
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import easyocr
from ..core.errors import ProcessingError
from ..models.common import SceneCut, VideoMetadata

# Initialize EasyOCR reader
EASYOCR_READER = easyocr.Reader(['en'], gpu=False)

class SceneProcessingService:
    def __init__(self, threshold: float = 0.22, frame_delay: float = 0.5, 
                 target_width: int = 640, target_bitrate: str = "800k"):
        """
        Initialize the scene processing service.
        
        Args:
            threshold: Threshold for scene detection (0.0 to 1.0, higher = more sensitive)
                      A value of 0.22 means 22% of pixels need to change to trigger a scene cut
            frame_delay: Number of seconds to wait after a scene cut before taking the frame
                        Default is 0.5 seconds to avoid transition frames
            target_width: Target width for downscaled video (height will be calculated to maintain aspect ratio)
            target_bitrate: Target bitrate for video compression (e.g. "800k" for 800 kbps)
        """
        self.threshold = threshold
        self.frame_delay = frame_delay
        self.target_width = target_width
        self.target_bitrate = target_bitrate
        
    def _create_optimized_video(self, input_path: str) -> str:
        """
        Create an optimized version of the video (downscaled, no audio, compressed).
        Returns the path to the optimized video.
        """
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            output_path = temp_file.name
            
        try:
            # Get video info to calculate height while maintaining aspect ratio
            probe_cmd = [
                'ffprobe', '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height',
                '-of', 'json',
                input_path
            ]
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
            video_info = json.loads(probe_result.stdout)
            stream = video_info['streams'][0]
            
            # Calculate new height maintaining aspect ratio
            orig_width = int(stream['width'])
            orig_height = int(stream['height'])
            new_height = int((self.target_width / orig_width) * orig_height)
            
            # Ensure height is even (required by some codecs)
            new_height = new_height + (new_height % 2)
            
            # Create optimized video
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-an',  # Remove audio
                '-vf', f'scale={self.target_width}:{new_height}',
                '-c:v', 'libx264',
                '-preset', 'medium',  # Balance between compression speed and quality
                '-crf', '23',  # Constant Rate Factor (18-28 is good, lower = better quality)
                '-b:v', self.target_bitrate,
                '-maxrate', self.target_bitrate,
                '-bufsize', str(int(self.target_bitrate[:-1]) * 2) + 'k',  # 2x bitrate for buffer
                '-movflags', '+faststart',  # Enable fast start for web playback
                output_path
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            
            return output_path
            
        except Exception as e:
            if os.path.exists(output_path):
                os.unlink(output_path)
            raise ProcessingError(f"Failed to create optimized video: {str(e)}")
            
    async def process_video(self, video_path: str, metadata: VideoMetadata) -> Dict[str, Any]:
        """
        Process a video file to detect scenes and extract frames.
        
        Args:
            video_path: Path to the video file
            metadata: Video metadata
            
        Returns:
            Dictionary containing:
            {
                "scenes": [
                    {
                        "start": float,  # Start time in seconds
                        "end": float,    # End time in seconds
                        "text": str,     # OCR text from frame
                        "confidence": float  # Scene detection confidence
                    },
                    ...
                ],
                "metadata": {
                    "duration": float,   # Video duration in seconds
                    "fps": float,        # Video FPS
                    "resolution": str,   # Video resolution (e.g. "640x360")
                    "format": str,       # Video format (e.g. "h264")
                    "size_bytes": int    # Size of optimized video in bytes
                },
                "video_base64": str      # Base64-encoded optimized video
            }
            
        Raises:
            ProcessingError: If processing fails
        """
        try:
            # Create frames directory for temporary frame extraction
            frames_dir = os.path.join(os.path.dirname(video_path), 'frames')
            os.makedirs(frames_dir, exist_ok=True)
            
            # Create optimized video
            optimized_path = self._create_optimized_video(video_path)
            
            try:
                # Get video metadata using ffprobe
                probe_cmd = [
                    'ffprobe', '-v', 'error',
                    '-select_streams', 'v:0',
                    '-show_entries', 'stream=width,height,r_frame_rate,codec_name',
                    '-of', 'json',
                    optimized_path
                ]
                probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
                video_info = json.loads(probe_result.stdout)
                stream = video_info['streams'][0]
                
                # Calculate FPS from fraction
                fps_parts = stream['r_frame_rate'].split('/')
                fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 30.0
                
                # Run scene detection in a thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                scene_cuts = await loop.run_in_executor(None, self._detect_scenes, video_path, frames_dir)
                
                # Process each scene to perform OCR
                processed_scenes = []
                for start_time, frame_path in scene_cuts:
                    try:
                        # Get end time from next scene or video duration
                        end_time = None
                        for next_start, _ in scene_cuts:
                            if next_start > start_time:
                                end_time = next_start
                                break
                        if end_time is None and metadata.duration:
                            end_time = metadata.duration
                            
                        # Perform OCR on the frame
                        text = await self._perform_ocr(frame_path) if frame_path else None
                        
                        scene_data = {
                            "start": round(start_time, 3),  # Round to 3 decimal places for cleaner JSON
                            "end": round(end_time, 3) if end_time else None,
                            "text": text,
                            "confidence": 1.0  # ffmpeg scene detection is binary
                        }
                        processed_scenes.append(scene_data)
                    except Exception as e:
                        print(f"Warning: Failed to process scene at {start_time}s: {str(e)}")
                        # Add the scene anyway, but without OCR data
                        processed_scenes.append({
                            "start": round(start_time, 3),
                            "end": round(end_time, 3) if end_time else None,
                            "text": None,
                            "confidence": 1.0
                        })
                
                # Read optimized video and convert to base64
                with open(optimized_path, 'rb') as f:
                    video_bytes = f.read()
                    video_base64 = base64.b64encode(video_bytes).decode('utf-8')
                
                # Prepare final output
                output = {
                    "scenes": processed_scenes,
                    "metadata": {
                        "duration": round(metadata.duration, 3) if metadata.duration else None,
                        "fps": round(fps, 3),
                        "resolution": f"{stream['width']}x{stream['height']}",
                        "format": stream['codec_name'],
                        "size_bytes": len(video_bytes)
                    },
                    "video_base64": video_base64
                }
                
                # Save to JSON file
                output_path = os.path.join(os.path.dirname(video_path), 'scenes.json')
                with open(output_path, 'w') as f:
                    json.dump(output, f, indent=2)
                
                return output
                
            finally:
                # Clean up temporary files
                if os.path.exists(optimized_path):
                    os.unlink(optimized_path)
                if os.path.exists(frames_dir):
                    for file in os.listdir(frames_dir):
                        os.unlink(os.path.join(frames_dir, file))
                    os.rmdir(frames_dir)
            
        except Exception as e:
            raise ProcessingError(f"Failed to process video: {str(e)}")
            
    def _detect_scenes(self, video_path: str, frames_dir: str) -> List[Tuple[float, str]]:
        """
        Detect scene cuts in a video using ffmpeg and extract frames.
        
        Args:
            video_path: Path to the video file
            frames_dir: Directory to save extracted frames
            
        Returns:
            List of (timestamp, frame_path) tuples
        """
        # Extract first frame
        first_frame_path = os.path.join(frames_dir, 'cut_0000.jpg')
        first_frame_cmd = [
            'ffmpeg', '-i', video_path,
            '-vf', 'select=eq(n\,0)',
            '-vframes', '1',
            first_frame_path
        ]
        subprocess.run(first_frame_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Extract frames at scene cuts
        frame_pattern = os.path.join(frames_dir, 'cut_%04d.jpg')
        cmd = [
            'ffmpeg', '-i', video_path,
            '-vf', f"select='gt(scene,{self.threshold})',showinfo",
            '-vsync', 'vfr', frame_pattern,
            '-f', 'null', '-'
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Get timestamps from ffmpeg output
        timestamps = [0.0]  # Start with first frame
        for line in result.stderr.split('\n'):
            if 'showinfo' in line and 'pts_time:' in line:
                match = re.search(r'pts_time:([0-9.]+)', line)
                if match:
                    timestamps.append(float(match.group(1)))
        
        # Get extracted frames
        frames = sorted([os.path.join(frames_dir, f) for f in os.listdir(frames_dir) 
                        if f.startswith('cut_') and f.endswith('.jpg')])
        
        if len(timestamps) != len(frames):
            print(f"Warning: Number of timestamps ({len(timestamps)}) doesn't match number of frames ({len(frames)})")
            min_len = min(len(timestamps), len(frames))
            timestamps = timestamps[:min_len]
            frames = frames[:min_len]
            
        return list(zip(timestamps, frames))
        
    async def _perform_ocr(self, frame_path: str) -> str:
        """
        Perform OCR on a frame using EasyOCR with Tesseract as fallback.
        
        Args:
            frame_path: Path to the frame image
            
        Returns:
            Extracted text from the frame
        """
        if not frame_path:
            return ""
            
        loop = asyncio.get_event_loop()
        
        def _ocr():
            try:
                # Try EasyOCR first
                result = EASYOCR_READER.readtext(frame_path, detail=0)
                text = ' '.join(result)
                text = self._clean_text(text)
                if text.strip():
                    return text
                    
                # If EasyOCR fails or returns no text, try Tesseract
                image = Image.open(frame_path)
                text = pytesseract.image_to_string(image, config='--psm 6')
                text = self._clean_text(text)
                
                if not text.strip():
                    # Try with preprocessing
                    preprocessed = self._preprocess_image(frame_path)
                    text = pytesseract.image_to_string(preprocessed, config='--psm 6')
                    text = self._clean_text(text)
                    
                return text
            except Exception as e:
                print(f"OCR failed for {frame_path}: {str(e)}")
                return ""
                
        return await loop.run_in_executor(None, _ocr)
        
    def _preprocess_image(self, image_path: str) -> Image.Image:
        """Preprocess image for better OCR results."""
        image = Image.open(image_path).convert('L')
        image = image.filter(ImageFilter.MedianFilter())
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2)
        return image
        
    def _clean_text(self, text: str) -> str:
        """Clean OCR text by removing special characters and normalizing whitespace."""
        # Remove special characters but keep basic punctuation
        text = ''.join(c for c in text if c.isprintable() or c in string.punctuation)
        # Normalize whitespace
        text = ' '.join(text.split())
        return text.strip() 