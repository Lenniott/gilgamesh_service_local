import pytest
import asyncio
import os
import tempfile
from pathlib import Path
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

@pytest.fixture(scope="session")
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir

@pytest.fixture(autouse=True)
def mock_environment(monkeypatch):
    """Set up test environment variables."""
    # Mock environment variables that might be needed
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "true")
    
    # Create a temporary directory for test files
    test_temp_dir = tempfile.mkdtemp()
    monkeypatch.setenv("TEMP_DIR", test_temp_dir)
    
    yield
    
    # Cleanup
    if os.path.exists(test_temp_dir):
        for root, dirs, files in os.walk(test_temp_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(test_temp_dir)

@pytest.fixture
def mock_video_file(tmp_path):
    """Create a mock video file for testing."""
    video_path = tmp_path / "test_video.mp4"
    with open(video_path, 'wb') as f:
        f.write(b'mock video content')
    return str(video_path)

@pytest.fixture
def mock_audio_file(tmp_path):
    """Create a mock audio file for testing."""
    audio_path = tmp_path / "test_audio.mp3"
    with open(audio_path, 'wb') as f:
        f.write(b'mock audio content')
    return str(audio_path) 