from pydantic import BaseModel, Field, HttpUrl, field_validator, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ProcessingStatusEnum(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TranscriptSegment(BaseModel):
    """Represents a segment of transcribed text with timing information."""
    text: str = Field(..., description="The transcribed text")
    start: float = Field(..., ge=0, description="Start time in seconds")
    end: float = Field(..., ge=0, description="End time in seconds")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Confidence score of the transcription")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "text": "Hello, this is a test",
            "start": 1.5,
            "end": 3.2,
            "confidence": 0.95
        }
    })

class SceneCut(BaseModel):
    """Represents a scene cut with timing and metadata."""
    start_time: float = Field(..., ge=0, description="Start time of the scene in seconds")
    end_time: float = Field(..., ge=0, description="End time of the scene in seconds")
    onscreen_text: Optional[str] = Field(None, description="Text detected in the scene")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Confidence score of the scene detection")

    @field_validator('end_time')
    @classmethod
    def validate_end_time(cls, v, values):
        start_time = values.data.get('start_time')
        if start_time is not None and v <= start_time:
            raise ValueError('end_time must be greater than start_time')
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "start_time": 5.0,
            "end_time": 7.0,
            "onscreen_text": "Welcome to the video",
            "confidence": 0.85
        }
    })

class VideoMetadata(BaseModel):
    """Metadata about a video file."""
    duration: Optional[float] = Field(None, ge=0, description="Duration in seconds")
    width: Optional[int] = Field(None, gt=0, description="Video width in pixels")
    height: Optional[int] = Field(None, gt=0, description="Video height in pixels")
    format: Optional[str] = Field(None, description="Video format (e.g., mp4, webm)")
    fps: Optional[float] = Field(None, gt=0, description="Frames per second")
    size_bytes: Optional[int] = Field(None, gt=0, description="File size in bytes")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "duration": 120.5,
            "width": 1920,
            "height": 1080,
            "format": "mp4",
            "fps": 30.0,
            "size_bytes": 15000000
        }
    })

class ProcessingStatus(BaseModel):
    """Represents the current status of a processing task."""
    status: ProcessingStatusEnum = Field(..., description="Current processing status")
    progress: float = Field(0.0, ge=0.0, le=1.0, description="Progress from 0 to 1")
    message: Optional[str] = Field(None, description="Status message or error description")
    error: Optional[str] = Field(None, description="Error message if status is failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of the status update")
    task_id: Optional[str] = Field(None, description="Unique identifier for the processing task")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "status": "processing",
            "progress": 0.5,
            "message": "Processing video scenes",
            "timestamp": "2024-03-20T10:00:00Z",
            "task_id": "task_123"
        }
    })

class MediaType(str, Enum):
    """Type of media being processed."""
    VIDEO = "video"
    IMAGE = "image"
    AUDIO = "audio"

class MediaItem(BaseModel):
    """Base model for media items (videos, images, audio)."""
    type: MediaType
    url: Optional[HttpUrl] = Field(None, description="Source URL of the media")
    local_path: Optional[str] = Field(None, description="Local path to the media file")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata about the media")

class MediaMetadata(BaseModel):
    """Metadata about downloaded media."""
    source: str = Field(..., description="Source platform (e.g., 'youtube', 'instagram')")
    title: str = Field(default="", description="Media title if available")
    description: str = Field(default="", description="Media description or caption")
    tags: List[str] = Field(default_factory=list, description="List of tags or hashtags")
    upload_date: str = Field(default="", description="Upload date in YYYYMMDD format")
    duration: float = Field(default=0.0, description="Duration in seconds")
    is_carousel: bool = Field(default=False, description="Whether this is a carousel post")
    media_type: MediaType = Field(default=MediaType.VIDEO, description="Type of media (video, image, audio)")
    media_count: int = Field(default=1, description="Number of media items in the post (for carousels)")

class DownloadResult(BaseModel):
    """Result of a media download operation."""
    files: List[str] = Field(..., description="List of downloaded file paths")
    metadata: MediaMetadata = Field(..., description="Media metadata")
    temp_dir: str = Field(..., description="Temporary directory containing the files")
    original_url: str = Field(..., description="Original URL that was downloaded")
    download_time: datetime = Field(default_factory=datetime.now, description="When the download completed")

class ProcessingStatus(BaseModel):
    """Status of media processing."""
    status: str = Field(..., description="Current status (e.g., 'downloading', 'processing', 'completed')")
    progress: float = Field(default=0.0, description="Progress from 0.0 to 1.0")
    error: Optional[str] = Field(default=None, description="Error message if any")
    result: Optional[DownloadResult] = Field(default=None, description="Download result if completed") 