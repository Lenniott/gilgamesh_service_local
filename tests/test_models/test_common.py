import pytest
from datetime import datetime
from app.models.common import (
    ProcessingStatusEnum,
    TranscriptSegment,
    SceneCut,
    VideoMetadata,
    ProcessingStatus,
    MediaType,
    MediaItem
)

def test_transcript_segment():
    # Test valid segment
    segment = TranscriptSegment(
        text="Hello world",
        start=1.0,
        end=2.0,
        confidence=0.95
    )
    assert segment.text == "Hello world"
    assert segment.start == 1.0
    assert segment.end == 2.0
    assert segment.confidence == 0.95

    # Test invalid start time
    with pytest.raises(ValueError):
        TranscriptSegment(
            text="Hello world",
            start=-1.0,
            end=2.0
        )

    # Test invalid confidence
    with pytest.raises(ValueError):
        TranscriptSegment(
            text="Hello world",
            start=1.0,
            end=2.0,
            confidence=1.5
        )

def test_scene_cut():
    # Test valid cut
    cut = SceneCut(
        start_time=1.0,
        end_time=2.0,
        onscreen_text="Welcome",
        confidence=0.85
    )
    assert cut.start_time == 1.0
    assert cut.end_time == 2.0
    assert cut.onscreen_text == "Welcome"
    assert cut.confidence == 0.85

    # Test invalid start time
    with pytest.raises(ValueError):
        SceneCut(
            start_time=-1.0,
            end_time=2.0
        )

def test_video_metadata():
    # Test valid metadata
    metadata = VideoMetadata(
        duration=120.5,
        width=1920,
        height=1080,
        format="mp4",
        fps=30.0,
        size_bytes=15000000
    )
    assert metadata.duration == 120.5
    assert metadata.width == 1920
    assert metadata.height == 1080
    assert metadata.format == "mp4"
    assert metadata.fps == 30.0
    assert metadata.size_bytes == 15000000

    # Test invalid width
    with pytest.raises(ValueError):
        VideoMetadata(
            duration=120.5,
            width=0,
            height=1080
        )

def test_processing_status():
    # Test valid status
    status = ProcessingStatus(
        status=ProcessingStatusEnum.PROCESSING,
        progress=0.5,
        message="Processing video",
        task_id="task_123"
    )
    assert status.status == ProcessingStatusEnum.PROCESSING
    assert status.progress == 0.5
    assert status.message == "Processing video"
    assert status.task_id == "task_123"
    assert isinstance(status.timestamp, datetime)

    # Test invalid progress
    with pytest.raises(ValueError):
        ProcessingStatus(
            status=ProcessingStatusEnum.PROCESSING,
            progress=1.5
        )

def test_media_item():
    # Test valid media item
    item = MediaItem(
        type=MediaType.VIDEO,
        url="https://example.com/video.mp4",
        local_path="/tmp/video.mp4",
        metadata={"duration": 120.5}
    )
    assert item.type == MediaType.VIDEO
    assert str(item.url) == "https://example.com/video.mp4"
    assert item.local_path == "/tmp/video.mp4"
    assert item.metadata == {"duration": 120.5}

    # Test invalid media type
    with pytest.raises(ValueError):
        MediaItem(
            type="invalid_type"
        ) 