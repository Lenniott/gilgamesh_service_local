import pytest
import asyncio
import os
from typing import Generator
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

pytest.register_marker("integration", "mark integration tests (e.g. download integration)")

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
def clean_test_env():
    """Clean up any test artifacts before and after each test."""
    # Setup
    yield
    # Teardown
    # Add any cleanup code here if needed

@pytest.fixture
def sample_transcript_segment():
    return TranscriptSegment(
        text="Hello world",
        start=1.0,
        end=2.0,
        confidence=0.95
    )

@pytest.fixture
def sample_scene_cut():
    return SceneCut(
        start_time=1.0,
        end_time=2.0,
        onscreen_text="Welcome",
        confidence=0.85
    )

@pytest.fixture
def sample_video_metadata():
    return VideoMetadata(
        duration=120.5,
        width=1920,
        height=1080,
        format="mp4",
        fps=30.0,
        size_bytes=15000000
    )

@pytest.fixture
def sample_processing_status():
    return ProcessingStatus(
        status=ProcessingStatusEnum.PROCESSING,
        progress=0.5,
        message="Processing video",
        task_id="task_123"
    )

@pytest.fixture
def sample_media_item():
    return MediaItem(
        type=MediaType.VIDEO,
        url="https://example.com/video.mp4",
        local_path="/tmp/video.mp4",
        metadata={"duration": 120.5}
    )

@pytest.fixture
def sample_video_result(sample_transcript_segment, sample_scene_cut, sample_video_metadata, sample_processing_status):
    from app.models.response import VideoResult
    return VideoResult(
        url="https://example.com/video.mp4",
        local_path="/tmp/video.mp4",
        transcript=[sample_transcript_segment],
        cuts=[sample_scene_cut],
        metadata=sample_video_metadata,
        base64="base64_encoded_video",
        processing_status=sample_processing_status
    )

@pytest.fixture
def sample_process_response(sample_video_result, sample_media_item, sample_processing_status):
    from app.models.response import ProcessResponse
    return ProcessResponse(
        task_id="task_123",
        url="https://example.com/media",
        description="Example video",
        tags=["video", "test"],
        videos=[sample_video_result],
        images=[sample_media_item],
        processing_status=sample_processing_status
    ) 