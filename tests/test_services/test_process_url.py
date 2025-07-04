import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from app.media_utils import process_single_url
from app.downloaders import download_media_and_metadata
from app.scene_detection import extract_scene_cuts_and_frames
from app.transcription import transcribe_audio

# Test data
TEST_URLS = {
    'instagram_post': 'https://www.instagram.com/p/test123/',
    'instagram_reel': 'https://www.instagram.com/reel/test123/',
    'youtube': 'https://youtube.com/watch?v=test123',
    'youtube_short': 'https://youtube.com/shorts/test123'
}

MOCK_DOWNLOAD_RESULT = {
    'files': ['/tmp/test_video.mp4', '/tmp/test_image.jpg'],
    'tags': ['test', 'mock'],
    'description': 'Test description',
    'source': 'instagram',
    'temp_dir': '/tmp/test_dir',
    'link': TEST_URLS['instagram_post']
}

@pytest.fixture
def mock_download():
    """Mock the download_media_and_metadata function."""
    def sync_mock(*args, **kwargs):
        return MOCK_DOWNLOAD_RESULT
    with patch('app.media_utils.download_media_and_metadata', side_effect=sync_mock) as mock:
        yield mock

@pytest.fixture
def mock_scene_detection():
    """Mock the scene detection functions."""
    def sync_mock(*args, **kwargs):
        return [(0.0, '/tmp/frame1.jpg'), (5.0, '/tmp/frame2.jpg')]
    with patch('app.media_utils.extract_scene_cuts_and_frames', side_effect=sync_mock) as mock:
        yield mock



@pytest.fixture
def mock_transcription():
    """Mock the transcription function."""
    def sync_mock(*args, **kwargs):
        return [{"start": 0.0, "end": 5.0, "text": "Test transcription"}]
    with patch('app.media_utils.transcribe_audio', side_effect=sync_mock) as mock:
        yield mock

@pytest.fixture
def mock_extract_and_downscale_scene():
    """Mock the extract_and_downscale_scene function."""
    def sync_mock(*args, **kwargs):
        return "FAKE_BASE64_VIDEO_DATA"
    with patch('app.media_utils.extract_and_downscale_scene', side_effect=sync_mock) as mock:
        yield mock

@pytest.mark.asyncio
async def test_process_single_url_basic(mock_download, mock_scene_detection, mock_transcription, mock_extract_and_downscale_scene):
    """Test basic processing of a single URL."""
    result = await process_single_url(TEST_URLS['instagram_post'], threshold=0.22, encode_base64=False)
    
    # Verify the result structure
    assert 'url' in result
    assert 'title' in result
    assert 'description' in result
    assert 'tags' in result
    assert 'temp_dir' in result
    
    # Verify the content
    assert result['url'] == TEST_URLS['instagram_post']
    assert result['description'] == MOCK_DOWNLOAD_RESULT['description']
    assert result['tags'] == MOCK_DOWNLOAD_RESULT['tags']
    
    # Verify no base64 data when encode_base64 is False
    if 'videos' in result:
        for video in result['videos']:
            for scene in video.get('scenes', []):
                assert 'video' not in scene

@pytest.mark.asyncio
async def test_process_single_url_with_base64(mock_download, mock_scene_detection, mock_transcription, mock_extract_and_downscale_scene):
    """Test processing with base64 encoding enabled."""
    result = await process_single_url(TEST_URLS['instagram_post'], threshold=0.22, encode_base64=True)
    
    # Verify base64 data is present when encode_base64 is True
    if 'videos' in result:
        for video in result['videos']:
            for scene in video.get('scenes', []):
                assert 'video' in scene
                assert isinstance(scene['video'], str)  # Should be base64 string

@pytest.mark.asyncio
async def test_process_single_url_error_handling(mock_download, mock_extract_and_downscale_scene):
    """Test error handling in process_single_url."""
    # Make the download fail
    mock_download.side_effect = Exception("Download failed")
    
    with pytest.raises(Exception) as exc_info:
        await process_single_url(TEST_URLS['instagram_post'])
    
    assert "Download failed" in str(exc_info.value)

@pytest.mark.asyncio
async def test_process_single_url_cleanup(mock_download, mock_scene_detection, mock_transcription, mock_extract_and_downscale_scene):
    """Test that temporary files are properly managed."""
    import os
    import shutil
    
    # Create a temporary directory for testing
    test_dir = '/tmp/gilgamesh_test'
    os.makedirs(test_dir, exist_ok=True)
    
    try:
        # Mock the temp directory creation
        with patch('app.media_utils.os.path.join', return_value=test_dir):
            result = await process_single_url(TEST_URLS['instagram_post'])
            
            # Verify temp directory exists
            assert os.path.exists(result['temp_dir'])
            
            # Verify temp directory is empty after processing
            assert len(os.listdir(result['temp_dir'])) == 0
    finally:
        # Cleanup
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir) 