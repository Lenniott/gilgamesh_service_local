import os
import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import HttpUrl
from ..core.errors import ProcessingError
from ..models.response import ProcessResponse, Video, Scene, Image
from ..models.common import MediaType
from ..models.request import ProcessRequest
from .download import AsyncDownloadService
from .scene_processing import SceneProcessingService
from .transcription import TranscriptionService
import tempfile
import shutil
from pathlib import Path
from urllib.parse import urlparse
import pytesseract
from PIL import Image

# Configure logging
logger = logging.getLogger(__name__)

class MediaProcessingService:
    def __init__(self):
        """Initialize the media processing service with all required components."""
        logger.info("Initializing MediaProcessingService")
        self.download_service = AsyncDownloadService()
        self.scene_processor = None  # Initialize on first use with parameters
        self.transcription_service = None  # Initialize on first use with parameters
        self._temp_dir = None
        self._debug_mode = False

    @property
    def temp_dir(self) -> Path:
        if self._temp_dir is None:
            self._temp_dir = Path(tempfile.mkdtemp(prefix="gilgamesh_media_"))
        return self._temp_dir

    def _get_scene_processor(self, scene_threshold: float = 0.22) -> SceneProcessingService:
        """Get or create a scene processor with the given threshold."""
        if self.scene_processor is None or self.scene_processor.threshold != scene_threshold:
            logger.debug(f"Creating new scene processor with threshold {scene_threshold}")
            self.scene_processor = SceneProcessingService(threshold=scene_threshold)
        return self.scene_processor

    def _get_transcription_service(self) -> TranscriptionService:
        """Get or create a transcription service."""
        if self.transcription_service is None:
            logger.debug("Creating new transcription service")
            self.transcription_service = TranscriptionService()
        return self.transcription_service

    async def _download_media(self, url: str) -> Optional[Path]:
        """Download media from URL and return the path to the downloaded file."""
        try:
            logger.info(f"Downloading media from {url}")
            download_result = await self.download_service.download_media(url)
            
            if not download_result.files:
                logger.error(f"No files downloaded from {url}")
                return None
                
            # Get the first downloaded file
            file_path = download_result.files[0]
            logger.info(f"Successfully downloaded {file_path}")
            
            # Move the file to our temp directory
            temp_path = self.temp_dir / Path(file_path).name
            shutil.move(file_path, temp_path)
            
            # Clean up the original download directory
            if hasattr(download_result, 'temp_dir') and download_result.temp_dir:
                shutil.rmtree(download_result.temp_dir, ignore_errors=True)
                
            return temp_path
            
        except Exception as e:
            logger.error(f"Error downloading media from {url}: {str(e)}")
            return None

    async def process_media_url(self, url: str | HttpUrl, request: Optional[ProcessRequest] = None) -> ProcessResponse:
        """Process a single media URL with optional parameters from the request."""
        try:
            # Convert HttpUrl to string if needed
            url_str = str(url)
            
            # Get parameters from request or use defaults
            scene_threshold = request.scene_threshold if request else 0.22
            include_video_base64 = request.include_video_base64 if request else False
            max_duration = request.max_video_duration if request else None
            language = request.language if request else "en"
            self._debug_mode = request.debug_mode if request else False

            # Initialize services with parameters if needed
            if self.scene_processor is None:
                self.scene_processor = SceneProcessingService(threshold=scene_threshold)
            if self.transcription_service is None:
                self.transcription_service = TranscriptionService()

            # Download media
            media_path = await self._download_media(url_str)
            if not media_path:
                raise ValueError(f"Failed to download media from {url_str}")

            # Process based on file type
            if media_path.suffix.lower() in ['.mp4', '.mov', '.avi', '.mkv']:
                video_result = await self._process_video(media_path, include_video_base64, max_duration, language)
                if not video_result:
                    raise ValueError("Failed to process video")
                return ProcessResponse(
                    url=url_str,
                    title="",  # TODO: Get title from metadata
                    description="",  # TODO: Get description from metadata
                    tags=[],  # TODO: Get tags from metadata
                    videos=[video_result],
                    images=None
                )
            elif media_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                image_result = await self._process_image(media_path)
                if not image_result:
                    raise ValueError("Failed to process image")
                return ProcessResponse(
                    url=url_str,
                    title="",  # TODO: Get title from metadata
                    description="",  # TODO: Get description from metadata
                    tags=[],  # TODO: Get tags from metadata
                    videos=None,
                    images=[image_result]
                )
            else:
                raise ValueError(f"Unsupported file type: {media_path.suffix}")

        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)}")
            if not self._debug_mode:
                self._cleanup_temp_files()
            raise
        finally:
            # Clean up temporary files unless in debug mode
            if not self._debug_mode:
                self._cleanup_temp_files()
            else:
                logger.info(f"Debug mode enabled - keeping temporary files in: {self.temp_dir}")

    def _cleanup_temp_files(self):
        """Clean up temporary files and directory."""
        try:
            if self._temp_dir and self._temp_dir.exists():
                if self._debug_mode:
                    logger.info(f"Debug mode enabled - skipping cleanup of {self._temp_dir}")
                    return
                shutil.rmtree(self._temp_dir)
                self._temp_dir = None
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {str(e)}")

    async def _process_video(
        self,
        video_path: str,
        scene_threshold: float = 0.22,
        include_video_base64: bool = False,
        max_duration: Optional[float] = None,
        language: Optional[str] = None
    ) -> Optional[Video]:
        """Process a video file to extract scenes and transcript."""
        try:
            logger.debug(f"Processing video with parameters: threshold={scene_threshold}, "
                        f"include_base64={include_video_base64}, max_duration={max_duration}")
            
            # Get services with parameters
            scene_processor = self._get_scene_processor(scene_threshold)
            transcription_service = self._get_transcription_service()
            
            # Process scenes
            logger.info("Starting scene detection")
            scene_result = await scene_processor.process_video(video_path)
            
            # Get transcript
            logger.info("Starting video transcription")
            transcript = await transcription_service.transcribe_video(video_path)
            
            # Convert scenes to our format
            scenes = []
            for scene in scene_result["scenes"]:
                # Skip scenes beyond max_duration if specified
                if max_duration and scene["start_time"] >= max_duration:
                    break
                    
                scenes.append(Scene(
                    start=scene["start_time"],
                    end=min(scene["end_time"], max_duration) if max_duration else scene["end_time"],
                    text=scene["text"],
                    confidence=scene["confidence"]
                ))
            
            logger.info(f"Processed {len(scenes)} scenes from video")
            return Video(
                id=scene_result.get("id"),  # Will be generated if not present
                scenes=scenes,
                video=scene_result.get("video_base64") if include_video_base64 else None
            )
            
        except Exception as e:
            logger.error(f"Error processing video {video_path}: {str(e)}", exc_info=True)
            return None

    async def _process_image(self, image_path: str) -> Optional[Image]:
        """Process an image file to extract text."""
        try:
            logger.debug(f"Processing image: {image_path}")
            
            # Process image using default scene processor
            scene_processor = self._get_scene_processor()
            image_result = await scene_processor.process_image(image_path)
            
            # Get text from first scene (images only have one scene)
            text = ""
            if image_result and "scenes" in image_result and image_result["scenes"]:
                text = image_result["scenes"][0].get("text", "")
            
            logger.info("Successfully processed image")
            return Image(text=text)
            
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {str(e)}", exc_info=True)
            return None

    async def process_image(self, image_path: str) -> dict:
        """
        Simple OCR: Extract text from the image and return as {'text': ...}
        """
        try:
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img)
            return {"text": text.strip()}
        except Exception as e:
            # Return error in the expected structure
            return {"text": "", "error": str(e)}

    async def process_images(self, image_paths: list) -> list:
        """
        Process only the first image in the list, return OCR text.
        """
        if not image_paths:
            return [{"text": "", "error": "No images provided"}]
        result = await self.process_image(image_paths[0])
        return [result]

# Create a singleton instance
media_service = MediaProcessingService()

async def process_media_url(url: str, request: Optional[ProcessRequest] = None) -> ProcessResponse:
    """Process a single media URL using the singleton service instance."""
    return await media_service.process_media_url(url, request) 