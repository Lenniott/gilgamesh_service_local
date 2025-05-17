from pydantic import BaseModel, Field, HttpUrl, field_validator, ConfigDict
from typing import List, Optional
from .common import ProcessingStatusEnum
import re

class ProcessRequest(BaseModel):
    """Request model for processing multiple media URLs."""
    urls: List[HttpUrl] = Field(..., min_length=1, description="List of media URLs to process")
    scene_threshold: Optional[float] = Field(
        default=0.22,
        ge=0.0,
        le=1.0,
        description="Threshold for scene detection (0.0 to 1.0)"
    )
    include_video_base64: Optional[bool] = Field(
        default=False,
        description="Whether to include base64-encoded video in response"
    )
    max_video_duration: Optional[float] = Field(
        default=None,
        gt=0,
        description="Maximum video duration to process in seconds"
    )
    language: Optional[str] = Field(
        default="en",
        description="Language code for transcription (e.g., 'en', 'es', 'fr')"
    )
    debug_mode: Optional[bool] = Field(
        default=False,
        description="Enable debug mode to keep temporary files"
    )

    @field_validator('urls')
    @classmethod
    def validate_unique_urls(cls, v):
        if len(set(str(url) for url in v)) != len(v):
            raise ValueError('URLs must be unique')
        return v

    @field_validator('urls')
    @classmethod
    def validate_url_types(cls, v):
        """Validate that URLs are from supported platforms."""
        supported_patterns = [
            r'^https?://(?:www\.)?instagram\.com/(?:p|reel)/[^/]+/?.*$',  # Instagram posts and reels
            r'^https?://(?:www\.)?youtube\.com/shorts/[^/]+/?.*$',  # YouTube shorts
            r'^https?://youtu\.be/[^/]+/?.*$'  # YouTube short URLs
        ]
        
        for url in v:
            url_str = str(url)
            if not any(re.match(pattern, url_str) for pattern in supported_patterns):
                raise ValueError(f'Unsupported URL type: {url_str}. Only Instagram posts/reels and YouTube shorts are supported.')
        return v

    @field_validator('scene_threshold')
    @classmethod
    def validate_scene_threshold(cls, v):
        if v is not None and not 0 <= v <= 1:
            raise ValueError('scene_threshold must be between 0 and 1')
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "urls": [
                "https://www.instagram.com/p/DJpP_JPSKHK/?igsh=MmIyb2twNXc0ajNv",
                "https://www.instagram.com/p/DJRiA-gI2GT/?igsh=bXI4MWJzNnhhMm5t",
                "https://www.instagram.com/reel/DJVTMdRxRmJ/?igsh=eHJtN214OWpuMnIx",
                "https://youtube.com/shorts/izeO1Vpqvvo?si=blnnaTO0uYEe5htC"
            ],
            "scene_threshold": 0.22,
            "include_video_base64": False,
            "max_video_duration": 300,
            "language": "en",
            "debug_mode": False
        }
    })

class BatchProcessRequest(BaseModel):
    """Request model for processing multiple media URLs."""
    urls: List[HttpUrl] = Field(..., min_length=1, max_length=10, description="List of media URLs to process")
    include_video_base64: bool = Field(False, description="Whether to include base64-encoded videos in response")
    scene_threshold: float = Field(0.22, ge=0.0, le=1.0, description="Threshold for scene detection")
    max_video_duration: Optional[float] = Field(None, gt=0, description="Maximum video duration to process in seconds")
    language: Optional[str] = Field(None, description="Language code for transcription (e.g., 'en', 'es')")
    parallel_processing: bool = Field(True, description="Whether to process videos in parallel")

    @field_validator('urls')
    @classmethod
    def validate_unique_urls(cls, v):
        if len(set(str(url) for url in v)) != len(v):
            raise ValueError('URLs must be unique')
        return v

    @field_validator('scene_threshold')
    @classmethod
    def validate_scene_threshold(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('scene_threshold must be between 0 and 1')
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "urls": [
                "https://example.com/video1.mp4",
                "https://example.com/video2.mp4"
            ],
            "include_video_base64": False,
            "scene_threshold": 0.22,
            "max_video_duration": 300,
            "language": "en",
            "parallel_processing": True
        }
    })

class StatusRequest(BaseModel):
    """Request model for checking processing status."""
    task_id: str = Field(..., description="Task ID to check status for")

    @field_validator('task_id')
    @classmethod
    def validate_task_id(cls, v):
        if not v or not v.strip():
            raise ValueError('task_id must not be empty')
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "task_id": "task_123"
        }
    }) 