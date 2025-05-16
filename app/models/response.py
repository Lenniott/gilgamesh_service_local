from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from .common import (
    TranscriptSegment,
    SceneCut,
    VideoMetadata,
    ProcessingStatus,
    ProcessingStatusEnum,
    MediaType,
    MediaItem
)

class VideoResult(BaseModel):
    """Result model for a processed video."""
    url: Optional[HttpUrl] = Field(None, description="Original video URL")
    local_path: Optional[str] = Field(None, description="Local path to the processed video")
    transcript: List[TranscriptSegment] = Field(default_factory=list, description="Video transcript segments")
    cuts: List[SceneCut] = Field(default_factory=list, description="Detected scene cuts")
    metadata: VideoMetadata = Field(..., description="Video metadata")
    base64: Optional[str] = Field(None, description="Base64-encoded video data")
    processing_status: ProcessingStatus = Field(..., description="Processing status of the video")

    class Config:
        schema_extra = {
            "example": {
                "url": "https://example.com/video.mp4",
                "transcript": [
                    {
                        "text": "Hello, this is a test",
                        "start": 1.5,
                        "end": 3.2,
                        "confidence": 0.95
                    }
                ],
                "cuts": [
                    {
                        "start_time": 5.0,
                        "end_time": 7.0,
                        "onscreen_text": "Welcome to the video",
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
                "processing_status": {
                    "status": "completed",
                    "progress": 1.0,
                    "message": "Processing completed successfully",
                    "timestamp": "2024-03-20T10:00:00Z",
                    "task_id": "task_123"
                }
            }
        }

class ProcessResponse(BaseModel):
    """Response model for the processing endpoint."""
    task_id: str = Field(..., description="Unique identifier for the processing task")
    url: HttpUrl = Field(..., description="Original media URL")
    description: Optional[str] = Field(None, description="Media description or caption")
    tags: List[str] = Field(default_factory=list, description="Tags associated with the media")
    videos: List[VideoResult] = Field(default_factory=list, description="Processed video results")
    images: List[MediaItem] = Field(default_factory=list, description="Processed image results")
    processing_status: ProcessingStatus = Field(..., description="Overall processing status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when processing started")
    completed_at: Optional[datetime] = Field(None, description="Timestamp when processing completed")

    class Config:
        schema_extra = {
            "example": {
                "task_id": "task_123",
                "url": "https://example.com/media",
                "description": "Example video post",
                "tags": ["example", "video", "test"],
                "videos": [
                    {
                        "url": "https://example.com/video.mp4",
                        "transcript": [],
                        "cuts": [],
                        "metadata": {
                            "duration": 120.5,
                            "width": 1920,
                            "height": 1080
                        },
                        "processing_status": {
                            "status": "completed",
                            "progress": 1.0
                        }
                    }
                ],
                "images": [],
                "processing_status": {
                    "status": "completed",
                    "progress": 1.0
                },
                "created_at": "2024-03-20T10:00:00Z",
                "completed_at": "2024-03-20T10:01:00Z"
            }
        }

class BatchProcessResponse(BaseModel):
    """Response model for batch processing endpoint."""
    task_id: str = Field(..., description="Unique identifier for the batch processing task")
    results: List[ProcessResponse] = Field(..., description="Results for each processed URL")
    processing_status: ProcessingStatus = Field(..., description="Overall batch processing status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when processing started")
    completed_at: Optional[datetime] = Field(None, description="Timestamp when processing completed")

    class Config:
        schema_extra = {
            "example": {
                "task_id": "batch_123",
                "results": [
                    {
                        "task_id": "task_1",
                        "url": "https://example.com/video1.mp4",
                        "processing_status": {
                            "status": "completed",
                            "progress": 1.0
                        }
                    }
                ],
                "processing_status": {
                    "status": "processing",
                    "progress": 0.5
                },
                "created_at": "2024-03-20T10:00:00Z",
                "completed_at": None
            }
        }

class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the error occurred")

    @model_validator(mode="after")
    def check_status_code(self):
        if not (100 <= self.status_code <= 599):
            raise ValueError('status_code must be a valid HTTP status code (100-599)')
        return self

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "error": "Processing failed",
            "detail": "Video file could not be downloaded",
            "status_code": 500,
            "timestamp": "2024-03-20T10:00:00Z"
        }
    }) 