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
import uuid
from contextlib import asynccontextmanager
from typing import List, Optional, Tuple, Dict, Any, NamedTuple, AsyncGenerator
from pathlib import Path
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import easyocr
from ..core.errors import ProcessingError
from ..models.common import SceneCut, VideoMetadata

# Initialize EasyOCR reader
EASYOCR_READER = easyocr.Reader(['en'], gpu=False)

class SubprocessResult(NamedTuple):
    """Result from running a subprocess command."""
    stdout: str
    stderr: str
    returncode: int

class OCRPipeline:
    """Modular OCR pipeline with detector, enhancer, and recognizer components."""
    
    def __init__(self):
        self.reader = EASYOCR_READER
        
    async def detect_text_regions(self, image: Image.Image) -> List[Tuple[int, int, int, int]]:
        """Detect regions in the image that might contain text."""
        # Convert to numpy array for OpenCV
        img_array = np.array(image)
        # Convert to grayscale
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        # Apply threshold to get binary image
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # Filter and return bounding boxes
        regions = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > 20 and h > 20:  # Filter out tiny regions
                regions.append((x, y, x + w, y + h))
        return regions
        
    def enhance_image(self, image: Image.Image) -> Image.Image:
        """Enhance image for better OCR results."""
        # Convert to grayscale
        image = image.convert('L')
        # Apply median filter to reduce noise
        image = image.filter(ImageFilter.MedianFilter())
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2)
        return image
        
    async def recognize_text(self, image: Image.Image, regions: Optional[List[Tuple[int, int, int, int]]] = None) -> str:
        """Recognize text in the image using EasyOCR with Tesseract fallback."""
        try:
            # Try EasyOCR first
            if regions:
                # Process each region separately
                texts = []
                for x1, y1, x2, y2 in regions:
                    region = image.crop((x1, y1, x2, y2))
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, self.reader.readtext, np.array(region), {'detail': 0}
                    )
                    if result:  # Check if result is not empty
                        texts.extend([text for text in result if isinstance(text, str)])
            else:
                # Process entire image
                result = await asyncio.get_event_loop().run_in_executor(
                    None, self.reader.readtext, np.array(image), {'detail': 0}
                )
                if result:  # Check if result is not empty
                    texts = [text for text in result if isinstance(text, str)]
                else:
                    texts = []
                
            text = ' '.join(texts)
            text = self._clean_text(text)
            if text.strip():
                return text
                
            # If EasyOCR fails or returns no text, try Tesseract
            text = await asyncio.get_event_loop().run_in_executor(
                None, pytesseract.image_to_string, image, {'config': '--psm 6'}
            )
            text = self._clean_text(text)
            
            if not text.strip():
                # Try with enhanced image
                enhanced = self.enhance_image(image)
                text = await asyncio.get_event_loop().run_in_executor(
                    None, pytesseract.image_to_string, enhanced, {'config': '--psm 6'}
                )
                text = self._clean_text(text)
                
            return text
            
        except Exception as e:
            print(f"OCR failed: {str(e)}")
            return ""
            
    def _clean_text(self, text: str) -> str:
        """Clean OCR text by removing special characters and normalizing whitespace."""
        # Remove special characters but keep basic punctuation
        text = ''.join(c for c in text if c.isprintable() or c in string.punctuation)
        # Normalize whitespace
        text = ' '.join(text.split())
        return text.strip()

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
            target_width: Target width for downscaled video/images (height will be calculated to maintain aspect ratio)
            target_bitrate: Target bitrate for video compression (e.g. "800k" for 800 kbps)
        """
        self.threshold = threshold
        self.frame_delay = frame_delay
        self.target_width = target_width
        self.target_bitrate = target_bitrate
        self.ocr_pipeline = OCRPipeline()

    @asynccontextmanager
    async def _temp_directory(self) -> AsyncGenerator[str, None]:
        """Create a temporary directory that will be cleaned up automatically."""
        temp_dir = os.path.join(tempfile.gettempdir(), f"gilgamesh_{uuid.uuid4().hex}")
        os.makedirs(temp_dir, exist_ok=True)
        try:
            yield temp_dir
        finally:
            if os.path.exists(temp_dir):
                for file in os.listdir(temp_dir):
                    try:
                        os.unlink(os.path.join(temp_dir, file))
                    except Exception as e:
                        print(f"Warning: Failed to delete {file}: {e}")
                try:
                    os.rmdir(temp_dir)
                except Exception as e:
                    print(f"Warning: Failed to remove temp directory: {e}")

    @asynccontextmanager
    async def _temp_file(self, suffix: str = '.mp4') -> AsyncGenerator[str, None]:
        """Create a temporary file that will be cleaned up automatically."""
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_path = temp_file.name
        try:
            yield temp_path
        finally:
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    print(f"Warning: Failed to delete temp file: {e}")

    async def _run_subprocess(self, cmd: List[str], check: bool = True) -> SubprocessResult:
        """
        Run a subprocess command asynchronously.
        
        Args:
            cmd: Command to run as a list of strings
            check: If True, raise ProcessingError on non-zero return code
            
        Returns:
            SubprocessResult containing stdout, stderr, and return code
            
        Raises:
            ProcessingError: If check=True and command fails
        """
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                text=True
            )
            stdout, stderr = await process.communicate()
            
            if check and process.returncode != 0:
                raise ProcessingError(f"Command failed with code {process.returncode}: {stderr}")
                
            return SubprocessResult(stdout, stderr, process.returncode)
            
        except Exception as e:
            raise ProcessingError(f"Failed to run command {' '.join(cmd)}: {str(e)}")

    async def _create_optimized_video(self, input_path: str, output_path: str) -> None:
        """
        Create an optimized version of the video (downscaled, no audio, compressed).
        Returns the path to the optimized video.
        """
        try:
            # Get video info to calculate height while maintaining aspect ratio
            probe_cmd = [
                'ffprobe', '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height',
                '-of', 'json',
                input_path
            ]
            result = await self._run_subprocess(probe_cmd)
            video_info = json.loads(result.stdout)
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
            await self._run_subprocess(cmd)
            
        except Exception as e:
            if os.path.exists(output_path):
                os.unlink(output_path)
            raise ProcessingError(f"Failed to create optimized video: {str(e)}")

    async def process_media(self, file_path: str, media_type: str) -> Dict[str, Any]:
        """
        Process a media file (video or image) to extract text and metadata.
        
        Args:
            file_path: Path to the media file
            media_type: Type of media ('video' or 'image')
            
        Returns:
            Dict containing:
            - scenes: List of scene/text information
            - metadata: Media metadata
            - media_base64: Base64 encoded media (if applicable)
            - media_size: Size of the media in bytes
        """
        if media_type == 'video':
            return await self.process_video(file_path)
        elif media_type == 'image':
            return await self.process_image(file_path)
        else:
            raise ProcessingError(f"Unsupported media type: {media_type}")

    async def process_video(self, video_path: str) -> Dict[str, Any]:
        """
        Process a video file to detect scenes and perform OCR on each scene.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Dict containing:
            - scenes: List of scene information including timestamps and OCR text
            - metadata: Video metadata including resolution, fps, and codec
            - video_base64: Base64 encoded optimized video
            - video_size: Size of the optimized video in bytes
        """
        try:
            # Get video metadata
            metadata = await self._get_video_metadata(video_path)
            
            # Create optimized video
            async with self._temp_file(suffix='_optimized.mp4') as optimized_path:
                await self._create_optimized_video(video_path, optimized_path)
                
                # Read optimized video and convert to base64
                with open(optimized_path, 'rb') as f:
                    video_bytes = f.read()
                    video_base64 = base64.b64encode(video_bytes).decode('utf-8')
                    video_size = len(video_bytes)
            
            # Detect scenes
            async with self._temp_directory() as temp_dir:
                scenes = await self._detect_scenes(video_path, temp_dir)
                
                # Process each scene
                processed_scenes = []
                for scene in scenes:
                    # Extract frame at scene start
                    frame_path = os.path.join(temp_dir, f"frame_{scene.start_time:.2f}.jpg")
                    await self._extract_frame(video_path, scene.start_time, frame_path)
                    
                    # Perform OCR
                    text = await self._perform_ocr(frame_path)
                    
                    processed_scenes.append({
                        "start_time": round(scene.start_time, 2),
                        "end_time": round(scene.end_time, 2),
                        "text": text,
                        "confidence": scene.confidence
                    })
                    
                    # Clean up frame file
                    if os.path.exists(frame_path):
                        os.unlink(frame_path)
            
            # Create output structure
            result = {
                "scenes": processed_scenes,
                "metadata": {
                    "resolution": f"{metadata.width}x{metadata.height}",
                    "fps": metadata.fps,
                    "codec": metadata.codec,
                    "duration": metadata.duration,
                    "optimized_size_bytes": video_size,
                    "optimized_resolution": f"{self.target_width}p"
                },
                "video_base64": video_base64,
                "video_size": video_size
            }
            
            # Save to JSON file in same directory as video
            output_path = os.path.join(os.path.dirname(video_path), "scenes.json")
            with open(output_path, 'w') as f:
                json.dump(result, f, indent=2)
            
            return result
            
        except Exception as e:
            raise ProcessingError(f"Error processing video: {str(e)}")

    async def _extract_frame(self, video_path: str, timestamp: float, output_path: str) -> None:
        """Extract a single frame from the video at the specified timestamp."""
        cmd = [
            'ffmpeg', '-ss', str(timestamp),
            '-i', video_path,
            '-vframes', '1',
            '-q:v', '2',  # High quality
            output_path
        ]
        result = await self._run_subprocess(cmd)
        if result.returncode != 0:
            raise ProcessingError(f"Failed to extract frame: {result.stderr}")

    async def _perform_ocr(self, frame_path: str) -> str:
        """Perform OCR on a frame using the OCR pipeline."""
        try:
            image = Image.open(frame_path)
            # Detect text regions
            regions = await self.ocr_pipeline.detect_text_regions(image)
            # Try OCR with detected regions first
            if regions:
                text = await self.ocr_pipeline.recognize_text(image, regions)
                print(f"[DEBUG] EasyOCR (regions) result for {frame_path}: {repr(text)}")
                if text.strip():
                    return text
            # If no text found with regions, try full image
            text = await self.ocr_pipeline.recognize_text(image)
            print(f"[DEBUG] EasyOCR (full image) result for {frame_path}: {repr(text)}")
            return text
        except Exception as e:
            print(f"OCR failed for {frame_path}: {str(e)}")
            return ""

    async def _detect_scenes(self, video_path: str, frames_dir: str) -> List[SceneCut]:
        """
        Detect scene cuts in a video using ffmpeg and extract frames.
        
        Args:
            video_path: Path to the video file
            frames_dir: Directory to save extracted frames
            
        Returns:
            List of SceneCut objects
        """
        # Extract first frame
        first_frame_path = os.path.join(frames_dir, 'cut_0000.jpg')
        first_frame_cmd = [
            'ffmpeg', '-i', video_path,
            '-vf', 'select=eq(n\,0)',
            '-vframes', '1',
            first_frame_path
        ]
        await self._run_subprocess(first_frame_cmd)
        
        # Extract frames at scene cuts
        frame_pattern = os.path.join(frames_dir, 'cut_%04d.jpg')
        cmd = [
            'ffmpeg', '-i', video_path,
            '-vf', f"select='gt(scene,{self.threshold})',showinfo",
            '-vsync', 'vfr', frame_pattern,
            '-f', 'null', '-'
        ]
        result = await self._run_subprocess(cmd)
        
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
            
        return [SceneCut(start_time, end_time, frame_path) for start_time, end_time, frame_path in zip(timestamps[:-1], timestamps[1:], frames)]

    async def _get_video_metadata(self, video_path: str) -> VideoMetadata:
        """
        Get video metadata using ffprobe.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            VideoMetadata object containing metadata
        """
        try:
            # Get video info using ffprobe
            probe_cmd = [
                'ffprobe', '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height,r_frame_rate,codec_name',
                '-of', 'json',
                video_path
            ]
            result = await self._run_subprocess(probe_cmd)
            video_info = json.loads(result.stdout)
            stream = video_info['streams'][0]
            
            # Calculate FPS from fraction
            fps_parts = stream['r_frame_rate'].split('/')
            fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 30.0
            
            return VideoMetadata(
                width=int(stream['width']),
                height=int(stream['height']),
                fps=fps,
                codec=stream['codec_name'],
                duration=float(video_info['format']['duration']) if 'duration' in video_info['format'] else None
            )
            
        except Exception as e:
            raise ProcessingError(f"Failed to get video metadata: {str(e)}")

    async def process_image(self, image_path: str) -> Dict[str, Any]:
        """
        Process an image file to extract text and metadata.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dict containing:
            - scenes: List with single scene containing OCR text
            - metadata: Image metadata
        """
        try:
            # Get image metadata
            metadata = await self._get_image_metadata(image_path)
            
            # Perform OCR on the image
            text = await self._perform_ocr(image_path)
            print(f"[DEBUG] OCR extracted text for {image_path}: {repr(text)}")
            
            # Create a single "scene" for the image
            processed_scenes = [{
                "start_time": 0.0,
                "end_time": 0.0,
                "text": text,
                "confidence": 1.0  # Images are treated as single frames
            }]
            
            # Create output structure
            result = {
                "scenes": processed_scenes,
                "metadata": {
                    "resolution": f"{metadata.width}x{metadata.height}",
                    "format": metadata.format,
                    "size_bytes": metadata.size_bytes,
                    "optimized_resolution": f"{self.target_width}p"
                }
            }
            
            # Save to JSON file in same directory as image
            output_path = os.path.join(os.path.dirname(image_path), "scenes.json")
            with open(output_path, 'w') as f:
                json.dump(result, f, indent=2)
            
            return result
            
        except Exception as e:
            raise ProcessingError(f"Error processing image: {str(e)}")

    async def _get_image_metadata(self, image_path: str) -> VideoMetadata:
        """
        Get image metadata.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            VideoMetadata object containing metadata
        """
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                format = img.format.lower()
                size_bytes = os.path.getsize(image_path)
                
                return VideoMetadata(
                    width=width,
                    height=height,
                    format=format,
                    size_bytes=size_bytes,
                    fps=None,  # Not applicable for images
                    duration=None,  # Not applicable for images
                    codec=None  # Not applicable for images
                )
                
        except Exception as e:
            raise ProcessingError(f"Failed to get image metadata: {str(e)}") 