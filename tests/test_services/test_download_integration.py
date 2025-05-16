import pytest
import asyncio
from app.services.download import AsyncDownloadService
from app.core.errors import DownloadError, UnsupportedURLError

INSTAGRAM_VIDEO_URL = "https://www.instagram.com/reel/DJZVzosxBMA/"
INSTAGRAM_CAROUSEL_URL = "https://www.instagram.com/p/DJRiA-gI2GT/?img_index=1"
YOUTUBE_URL = "https://www.youtube.com/shorts/XQWnrf3wChw"

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(scope="function")]

@pytest.mark.asyncio
async def test_instagram_video_download(tmp_path):
    service = AsyncDownloadService(base_temp_dir=str(tmp_path))
    result = await service.download_media(INSTAGRAM_VIDEO_URL)
    assert result.metadata.source == 'instagram'
    assert result.metadata.is_carousel is False
    assert len(result.files) > 0
    print(f"Instagram video files: {result.files}")
    print(f"Metadata: {result.metadata}")
    print(f"Test output dir (Instagram): {result.temp_dir}")

@pytest.mark.asyncio
async def test_instagram_carousel_download(tmp_path):
    service = AsyncDownloadService(base_temp_dir=str(tmp_path))
    result = await service.download_media(INSTAGRAM_CAROUSEL_URL)
    assert result.metadata.source == 'instagram'
    assert result.metadata.is_carousel is True
    assert len(result.files) > 1
    print(f"Instagram carousel files: {result.files}")
    print(f"Metadata: {result.metadata}")
    print(f"Test output dir (Instagram carousel): {result.temp_dir}")

@pytest.mark.asyncio
async def test_youtube_download(tmp_path):
    service = AsyncDownloadService(base_temp_dir=str(tmp_path))
    result = await service.download_media(YOUTUBE_URL)
    assert result.metadata.source == 'youtube/tiktok'
    assert result.metadata.is_carousel is False
    assert len(result.files) > 0
    print(f"YouTube files: {result.files}")
    print(f"Metadata: {result.metadata}")
    print(f"Test output dir (YouTube): {result.temp_dir}") 