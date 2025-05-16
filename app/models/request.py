from pydantic import BaseModel, Field, HttpUrl, field_validator, ConfigDict
from typing import List, Optional
from .common import ProcessingStatusEnum

class ProcessRequest(BaseModel):
    """Request model for processing a single media URL."""
    url: HttpUrl = Field(..., description="URL of the media to process")
    include_video_base64: bool = Field(False, description="Whether to include base64-encoded video in response")
    scene_threshold: float = Field(0.22, ge=0.0, le=1.0, description="Threshold for scene detection")
    max_video_duration: Optional[float] = Field(None, gt=0, description="Maximum video duration to process in seconds")
    language: Optional[str] = Field(None, description="Language code for transcription (e.g., 'en', 'es')")

    @field_validator('scene_threshold')
    @classmethod
    def validate_scene_threshold(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('scene_threshold must be between 0 and 1')
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "url": "https://example.com/video.mp4",
            "include_video_base64": False,
            "scene_threshold": 0.22,
            "max_video_duration": 300,
            "language": "en"
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