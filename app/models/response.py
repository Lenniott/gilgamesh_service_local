from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from .common import ProcessingStatusEnum, TranscriptSegment, SceneCut, VideoMetadata, ProcessingStatus

class Scene(BaseModel):
    """Represents a scene with timing and text information."""
    start: float = Field(..., ge=0, description="Start time in seconds")
    end: float = Field(..., ge=0, description="End time in seconds")
    text: str = Field(..., description="Text detected in the scene")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score of the text detection")

    @field_validator('end')
    @classmethod
    def validate_end_time(cls, v, values):
        start = values.data.get('start')
        if start is not None and v <= start:
            raise ValueError('end must be greater than start')
        return v

class Video(BaseModel):
    """Represents a processed video with scenes and base64 data."""
    id: UUID = Field(default_factory=uuid4, description="Unique identifier for the video")
    scenes: List[Scene] = Field(default_factory=list, description="Detected scenes with text")
    video: Optional[str] = Field(None, description="Base64-encoded video data")

class Image(BaseModel):
    """Represents a processed image with OCR text."""
    text: str = Field(..., description="Text detected in the image")

class ProcessResponse(BaseModel):
    """Response model for the processing endpoint."""
    url: HttpUrl = Field(..., description="Original media URL")
    title: str = Field(..., description="Extracted title")
    description: str = Field(..., description="Extracted description")
    tags: List[str] = Field(default_factory=list, description="Extracted tags")
    videos: Optional[List[Video]] = Field(None, description="Processed videos if any")
    images: Optional[List[Image]] = Field(None, description="Processed images if any")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "url": "https://www.instagram.com/p/DJpP_JPSKHK/?igsh=MmIyb2twNXc0ajNv",
            "title": "Example Post Title",
            "description": "Example post description",
            "tags": ["tag1", "tag2"],
            "videos": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "scenes": [
                        {
                            "start": 0.0,
                            "end": 3.2,
                            "text": "Scene text 1",
                            "confidence": 0.95
                        }
                    ],
                    "video": "base64-encoded-string"
                }
            ],
            "images": [
                {
                    "text": "Text from image 1"
                }
            ]
        }
    })

class BatchProcessResponse(BaseModel):
    """Response model for batch processing endpoint."""
    results: List[ProcessResponse] = Field(..., description="Results for each processed URL")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "results": [
                {
                    "url": "https://www.instagram.com/p/DJpP_JPSKHK/?igsh=MmIyb2twNXc0ajNv",
                    "title": "Example Post 1",
                    "description": "Description 1",
                    "tags": ["tag1"],
                    "videos": [],
                    "images": []
                },
                {
                    "url": "https://www.instagram.com/p/DJRiA-gI2GT/?igsh=bXI4MWJzNnhhMm5t",
                    "title": "Example Post 2",
                    "description": "Description 2",
                    "tags": ["tag2"],
                    "videos": [],
                    "images": []
                }
            ]
        }
    })

class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    status_code: int = Field(..., description="HTTP status code")

    @model_validator(mode="after")
    def check_status_code(self):
        if not (100 <= self.status_code <= 599):
            raise ValueError('status_code must be a valid HTTP status code (100-599)')
        return self

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "error": "Processing failed",
            "detail": "Video file could not be downloaded",
            "status_code": 500
        }
    })

class VideoResult(BaseModel):
    """Represents a processed video with metadata and processing status."""
    url: HttpUrl = Field(..., description="Original video URL")
    local_path: str = Field(..., description="Local path to the downloaded video")
    transcript: List[TranscriptSegment] = Field(default_factory=list, description="Video transcript segments")
    cuts: List[SceneCut] = Field(default_factory=list, description="Detected scene cuts")
    metadata: VideoMetadata = Field(..., description="Video metadata")
    base64: Optional[str] = Field(None, description="Base64-encoded video data")
    processing_status: ProcessingStatus = Field(..., description="Current processing status")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "url": "https://example.com/video.mp4",
            "local_path": "/tmp/video.mp4",
            "transcript": [
                {
                    "text": "Hello world",
                    "start": 1.0,
                    "end": 2.0,
                    "confidence": 0.95
                }
            ],
            "cuts": [
                {
                    "start_time": 1.0,
                    "end_time": 2.0,
                    "onscreen_text": "Welcome",
                    "confidence": 0.85
                }
            ],
            "metadata": {
                "duration": 120.5,
                "width": 1920,
                "height": 1080,
                "format": "mp4",
                "fps": 30.0,
                "size_bytes": 15000000
            },
            "base64": "base64_encoded_video",
            "processing_status": {
                "status": "completed",
                "progress": 1.0,
                "message": "Processing completed",
                "task_id": "task_123"
            }
        }
    }) 