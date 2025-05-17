import pytest
import os
import time
import json
import threading
import asyncio
from datetime import datetime, timedelta
from app.cache import Cache

# Test data
TEST_URL = "https://www.instagram.com/p/test123/"
TEST_DATA = {
    "url": TEST_URL,
    "title": "Test Post",
    "description": "Test Description",
    "tags": ["test", "mock"],
    "videos": [{
        "id": "test_video",
        "scenes": [{
            "start": 0.0,
            "end": 5.0,
            "text": "Test scene",
            "video": "FAKE_BASE64_DATA"
        }]
    }]
}

@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create a temporary cache directory for testing."""
    cache_dir = tmp_path / "test_cache"
    cache_dir.mkdir()
    yield str(cache_dir)
    # Cleanup is handled by tmp_path fixture

@pytest.fixture
def cache(temp_cache_dir):
    """Create a cache instance with a temporary directory."""
    return Cache(cache_dir=temp_cache_dir, ttl_hours=1)

def test_cache_initialization(temp_cache_dir):
    """Test cache initialization with custom directory and TTL."""
    # Test with custom directory
    cache = Cache(cache_dir=temp_cache_dir, ttl_hours=2)
    assert os.path.abspath(cache.cache_dir) == os.path.abspath(temp_cache_dir)
    assert cache.ttl_seconds == 2 * 3600
    
    # Test with default directory
    cache = Cache(ttl_hours=24)
    expected_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'cache'))
    assert os.path.abspath(cache.cache_dir) == expected_dir
    assert cache.ttl_seconds == 24 * 3600

def test_cache_set_get(cache):
    """Test basic cache set and get operations."""
    # Test setting and getting data
    cache.set(TEST_URL, TEST_DATA)
    result = cache.get(TEST_URL)
    
    assert result is not None
    assert result['url'] == TEST_URL
    assert result['data']['title'] == TEST_DATA['title']
    assert result['data']['videos'][0]['scenes'][0]['video'] == "FAKE_BASE64_DATA"
    
    # Test getting non-existent URL
    assert cache.get("https://nonexistent.com") is None

def test_cache_ttl(cache):
    """Test cache TTL functionality."""
    # Set data with 1-hour TTL
    cache.set(TEST_URL, TEST_DATA)
    
    # Should be available immediately
    assert cache.get(TEST_URL) is not None
    
    # Modify TTL to 1 second for testing
    cache.ttl_seconds = 1
    time.sleep(1.1)  # Wait for TTL to expire
    
    # Should be expired
    assert cache.get(TEST_URL) is None

def test_cache_clear(cache):
    """Test cache clearing functionality."""
    # Add multiple entries
    urls = [f"https://test{i}.com" for i in range(3)]
    for url in urls:
        cache.set(url, {"url": url, "data": "test"})
    
    # Verify entries exist
    for url in urls:
        assert cache.get(url) is not None
    
    # Clear all entries
    cache.clear()
    for url in urls:
        assert cache.get(url) is None
    
    # Test clearing with age filter
    cache.set(TEST_URL, TEST_DATA)
    # Manually set the mtime to 2 seconds ago to simulate an old entry
    import glob
    import time
    cache_files = glob.glob(os.path.join(cache.cache_dir, '*.json'))
    for f in cache_files:
        os.utime(f, (time.time() - 2, time.time() - 2))
    # Clear entries older than 1 second
    cache.clear(older_than_hours=1/3600)  # 1 second in hours
    assert cache.get(TEST_URL) is None

def test_cache_thread_safety(cache):
    """Test cache thread safety with concurrent operations."""
    def worker(url, data, results, index):
        try:
            # Set data
            cache.set(url, data)
            # Get data
            result = cache.get(url)
            results[index] = result is not None and result['data'] == data
        except Exception as e:
            results[index] = str(e)
    
    # Create multiple threads
    threads = []
    results = [None] * 10
    for i in range(10):
        url = f"https://test{i}.com"
        data = {"url": url, "data": f"test{i}"}
        thread = threading.Thread(target=worker, args=(url, data, results, i))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads
    for thread in threads:
        thread.join()
    
    # Verify all operations succeeded
    assert all(results)

def test_cache_stats(cache):
    """Test cache statistics functionality."""
    # Add some test data
    for i in range(3):
        url = f"https://test{i}.com"
        cache.set(url, {"url": url, "data": "test"})
    
    # Get stats
    stats = cache.get_stats()
    
    # Verify stats
    assert stats['total_entries'] == 3
    assert stats['total_size_bytes'] > 0
    assert stats['oldest_entry'] is not None
    assert stats['newest_entry'] is not None
    assert stats['ttl_hours'] == 1

def test_cache_error_handling(cache, temp_cache_dir):
    """Test cache error handling."""
    # Test with invalid JSON data
    cache_path = os.path.join(temp_cache_dir, "invalid.json")
    with open(cache_path, 'w') as f:
        f.write("invalid json")
    
    # Should handle invalid JSON gracefully
    assert cache.get("invalid") is None
    
    # Test with read-only directory
    os.chmod(temp_cache_dir, 0o444)  # Read-only
    try:
        # Should handle permission error gracefully
        cache.set(TEST_URL, TEST_DATA)
        assert cache.get(TEST_URL) is None
    finally:
        os.chmod(temp_cache_dir, 0o755)  # Restore permissions 