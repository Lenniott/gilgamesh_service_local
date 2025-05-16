import pytest
from datetime import datetime
from app.models.response import (
    VideoResult,
    ProcessResponse,
    BatchProcessResponse,
    ErrorResponse
)
from app.models.common import (
    ProcessingStatusEnum,
    TranscriptSegment,
    SceneCut,
    VideoMetadata,
    ProcessingStatus,
    MediaType,
    MediaItem
)

def test_video_result():
    # Test valid result
    result = VideoResult(
        url="https://example.com/video.mp4",
        local_path="/tmp/video.mp4",
        transcript=[
            TranscriptSegment(
                text="Hello world",
                start=1.0,
                end=2.0,
                confidence=0.95
            )
        ],
        cuts=[
            SceneCut(
                start_time=1.0,
                end_time=2.0,
                onscreen_text="Welcome",
                confidence=0.85
            )
        ],
        metadata=VideoMetadata(
            duration=120.5,
            width=1920,
            height=1080,
            format="mp4",
            fps=30.0,
            size_bytes=15000000
        ),
        base64="base64_encoded_video",
        processing_status=ProcessingStatus(
            status=ProcessingStatusEnum.COMPLETED,
            progress=1.0,
            message="Processing completed",
            task_id="task_123"
        )
    )
    assert str(result.url) == "https://example.com/video.mp4"
    assert result.local_path == "/tmp/video.mp4"
    assert result.transcript[0].text == "Hello world"
    assert result.cuts[0].onscreen_text == "Welcome"
    assert result.metadata.width == 1920
    assert result.base64 == "base64_encoded_video"
    assert result.processing_status.status == ProcessingStatusEnum.COMPLETED

def test_process_response():
    # Test valid response
    response = ProcessResponse(
        task_id="task_123",
        url="https://example.com/media",
        description="Example video",
        tags=["video", "test"],
        videos=[
            VideoResult(
                metadata=VideoMetadata(duration=120.5),
                processing_status=ProcessingStatus(
                    status=ProcessingStatusEnum.COMPLETED,
                    progress=1.0
                )
            )
        ],
        images=[
            MediaItem(
                type=MediaType.IMAGE,
                url="https://example.com/image.jpg"
            )
        ],
        processing_status=ProcessingStatus(
            status=ProcessingStatusEnum.COMPLETED,
            progress=1.0
        )
    )
    assert response.task_id == "task_123"
    assert str(response.url) == "https://example.com/media"
    assert response.description == "Example video"
    assert response.tags == ["video", "test"]
    assert len(response.videos) == 1
    assert len(response.images) == 1
    assert response.processing_status.status == ProcessingStatusEnum.COMPLETED
    assert isinstance(response.created_at, datetime)

def test_batch_process_response():
    # Test valid response
    response = BatchProcessResponse(
        task_id="batch_123",
        results=[
            ProcessResponse(
                task_id="task_1",
                url="https://example.com/video1.mp4",
                processing_status=ProcessingStatus(
                    status=ProcessingStatusEnum.COMPLETED,
                    progress=1.0
                )
            )
        ],
        processing_status=ProcessingStatus(
            status=ProcessingStatusEnum.PROCESSING,
            progress=0.5
        )
    )
    assert response.task_id == "batch_123"
    assert len(response.results) == 1
    assert response.processing_status.status == ProcessingStatusEnum.PROCESSING
    assert response.processing_status.progress == 0.5
    assert isinstance(response.created_at, datetime)
    assert response.completed_at is None

def test_error_response():
    # Test valid error response
    error = ErrorResponse(
        error="Processing failed",
        detail="Video file could not be downloaded",
        status_code=500
    )
    assert error.error == "Processing failed"
    assert error.detail == "Video file could not be downloaded"
    assert error.status_code == 500
    assert isinstance(error.timestamp, datetime)

    # Test invalid status code
    with pytest.raises(ValueError):
        ErrorResponse(
            error="Processing failed",
            status_code=999  # Invalid HTTP status code
        )

def test_error_response_serialization():
    error = ErrorResponse(error="fail", status_code=400)
    data = error.model_dump()
    assert data["error"] == "fail"
    assert data["status_code"] == 400
    assert "timestamp" in data

def test_error_response_invalid_status_code():
    with pytest.raises(ValueError):
        ErrorResponse(error="fail", status_code=99)
    with pytest.raises(ValueError):
        ErrorResponse(error="fail", status_code=600) 