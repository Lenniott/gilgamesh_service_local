import os
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from app.services.download import AsyncDownloadService
from app.core.errors import DownloadError, UnsupportedURLError
from app.models.common import MediaMetadata, DownloadResult

# Set environment variable for testing
os.environ['PYTEST_CURRENT_TEST'] = 'true'

@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    return str(tmp_path)

@pytest.fixture
def download_service(temp_dir):
    """Create a download service instance with a test temp directory."""
    service = AsyncDownloadService(base_temp_dir=temp_dir)
    yield service
    # Cleanup after each test
    if os.path.exists(service.base_temp_dir):
        for item in os.listdir(service.base_temp_dir):
            item_path = os.path.join(service.base_temp_dir, item)
            if os.path.isdir(item_path):
                service._cleanup_temp_dir(item_path)

@pytest.mark.asyncio
async def test_unsupported_url(download_service):
    """Test that unsupported URLs raise UnsupportedURLError."""
    with pytest.raises(UnsupportedURLError):
        await download_service.download_media("https://unsupported.com/video")

@pytest.mark.asyncio
async def test_youtube_download_success(download_service):
    """Test successful YouTube download."""
    mock_info = {
        'title': 'Test Video',
        'description': 'Test Description',
        'tags': ['test', 'video'],
        'upload_date': '20240320',
        'duration': 120.5
    }
    
    mock_file = os.path.join(download_service.base_temp_dir, 'test_video.mp4')
    os.makedirs(os.path.dirname(mock_file), exist_ok=True)
    with open(mock_file, 'w') as f:
        f.write('test content')

    with patch('yt_dlp.YoutubeDL') as mock_ydl:
        mock_ydl_instance = Mock()
        mock_ydl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = mock_info
        
        result = await download_service.download_media("https://youtube.com/watch?v=test")
        
        assert isinstance(result, DownloadResult)
        assert result.metadata.source == 'youtube/tiktok'
        assert result.metadata.title == 'Test Video'
        assert result.metadata.description == 'Test Description'
        assert result.metadata.tags == ['test', 'video']
        assert result.metadata.upload_date == '20240320'
        assert result.metadata.duration == 120.5
        assert result.metadata.is_carousel is False
        assert result.original_url == "https://youtube.com/watch?v=test"
        assert len(result.files) > 0

@pytest.mark.asyncio
async def test_instagram_download_success(download_service):
    """Test successful Instagram download."""
    mock_post = Mock()
    mock_post.caption = "Test caption #test #video"
    mock_post.date_local = datetime.now()
    
    mock_file = os.path.join(download_service.base_temp_dir, 'test_post.jpg')
    os.makedirs(os.path.dirname(mock_file), exist_ok=True)
    with open(mock_file, 'w') as f:
        f.write('test content')

    with patch('instaloader.Instaloader') as mock_loader:
        mock_loader_instance = Mock()
        mock_loader.return_value = mock_loader_instance
        mock_loader_instance.download_post = Mock()
        
        with patch('instaloader.Post.from_shortcode', return_value=mock_post):
            result = await download_service.download_media("https://instagram.com/p/test")
            
            assert isinstance(result, DownloadResult)
            assert result.metadata.source == 'instagram'
            assert result.metadata.description == "Test caption #test #video"
            assert set(result.metadata.tags) == {'test', 'video'}
            assert result.metadata.is_carousel is False
            assert result.original_url == "https://instagram.com/p/test"
            assert len(result.files) > 0

@pytest.mark.asyncio
async def test_instagram_carousel_detection(download_service):
    """Test Instagram carousel post detection."""
    mock_post = Mock()
    mock_post.caption = "Test carousel"
    mock_post.date_local = datetime.now()
    # (Instead of "fake" files, "mock" post.typename (and post.mediacount) – "future-proof" carousel detection logic (for "async-first," "modular," "and" "maintainable" "refactor"))
    mock_post.typename = "GraphSidecar"
    mock_post.mediacount = 3
    with patch('instaloader.Instaloader') as mock_loader:
         mock_loader_instance = Mock()
         mock_loader.return_value = mock_loader_instance
         mock_loader_instance.download_post = Mock()
         with patch('instaloader.Post.from_shortcode', return_value=mock_post):
             result = await download_service.download_media("https://instagram.com/p/test")
             assert result.metadata.is_carousel is True
             assert len(result.files) == 3

@pytest.mark.asyncio
async def test_download_error_handling(download_service):
    """Test error handling during download."""
    with patch('yt_dlp.YoutubeDL') as mock_ydl:
        mock_ydl_instance = Mock()
        mock_ydl.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.side_effect = Exception("Download failed")
        
        with pytest.raises(DownloadError) as exc_info:
            await download_service.download_media("https://youtube.com/watch?v=test")
        
        assert "Download failed" in str(exc_info.value)
        # Verify temp directory was cleaned up
        assert not os.path.exists(download_service.base_temp_dir)

@pytest.mark.asyncio
async def test_cleanup_old_downloads(download_service):
    """Test cleanup of old download directories."""
    # Create some test directories with different ages
    now = datetime.now()
    old_dir = os.path.join(download_service.base_temp_dir, 'old_dir')
    new_dir = os.path.join(download_service.base_temp_dir, 'new_dir')
    
    os.makedirs(old_dir)
    os.makedirs(new_dir)
    
    # Create a test file in each directory
    with open(os.path.join(old_dir, 'test.txt'), 'w') as f:
        f.write('old content')
    with open(os.path.join(new_dir, 'test.txt'), 'w') as f:
        f.write('new content')
    
    # Set creation time of old directory to 25 hours ago
    old_time = now - timedelta(hours=25)
    os.utime(old_dir, (old_time.timestamp(), old_time.timestamp()))
    
    # Run cleanup
    await download_service.cleanup_old_downloads(max_age_hours=24)
    
    # Verify old directory was cleaned up but new directory remains
    assert not os.path.exists(old_dir)
    assert os.path.exists(new_dir)
    assert os.path.exists(os.path.join(new_dir, 'test.txt'))

def test_temp_dir_creation(download_service):
    """Test that temporary directories are created correctly."""
    temp_dir = download_service._create_temp_dir()
    assert os.path.exists(temp_dir)
    assert os.path.isdir(temp_dir)
    # Verify it's a UUID
    dir_name = os.path.basename(temp_dir)
    assert len(dir_name) == 36  # UUID length 