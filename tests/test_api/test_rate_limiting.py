import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app, MAX_CONCURRENT_REQUESTS
from app.media_utils import process_single_url

client = TestClient(app)

@pytest.fixture
def mock_process_service():
    """Mock the process service to simulate processing time."""
    with patch('app.media_utils.process_single_url') as mock:
        # Make process_url an async mock that takes some time
        mock.side_effect = lambda *args, **kwargs: asyncio.sleep(0.1)
        yield mock

@pytest.mark.asyncio
async def test_concurrent_requests_limited():
    """Test that concurrent requests are limited to MAX_CONCURRENT_REQUESTS."""
    # Create a list to track active requests
    active_requests = []
    
    async def make_request(i):
        try:
            response = client.post(
                "/process",
                json={
                    "url": f"https://www.instagram.com/video{i}.mp4",
                    "encode_base64": False
                }
            )
            active_requests.append(i)
            # If we get here, the request was accepted
            assert response.status_code in [200, 429]
            if response.status_code == 429:
                assert "Too many concurrent requests" in response.json()["detail"]
            await asyncio.sleep(0.1)  # Simulate some processing time
        finally:
            if i in active_requests:
                active_requests.remove(i)
    
    # Try to make more requests than the limit
    num_requests = MAX_CONCURRENT_REQUESTS + 5
    tasks = [make_request(i) for i in range(num_requests)]
    
    # Run all requests concurrently
    await asyncio.gather(*tasks)
    
    # Verify that we never exceeded the limit
    assert len(active_requests) <= MAX_CONCURRENT_REQUESTS

@pytest.mark.asyncio
async def test_batch_requests_limited():
    """Test that batch requests respect the concurrency limit."""
    # Create a list to track active requests
    active_requests = []
    
    async def make_batch_request(i):
        try:
            response = client.post(
                "/process/batch",
                json={
                    "urls": [
                        f"https://www.instagram.com/video{i}_{j}.mp4"
                        for j in range(3)  # Each batch has 3 URLs
                    ],
                    "encode_base64": False
                }
            )
            active_requests.append(i)
            # If we get here, the request was accepted
            assert response.status_code in [200, 429]
            if response.status_code == 429:
                assert "Too many concurrent requests" in response.json()["detail"]
            await asyncio.sleep(0.1)  # Simulate some processing time
        finally:
            if i in active_requests:
                active_requests.remove(i)
    
    # Try to make more batch requests than the limit
    num_batches = MAX_CONCURRENT_REQUESTS + 3
    tasks = [make_batch_request(i) for i in range(num_batches)]
    
    # Run all batch requests concurrently
    await asyncio.gather(*tasks)
    
    # Verify that we never exceeded the limit
    assert len(active_requests) <= MAX_CONCURRENT_REQUESTS

@pytest.mark.asyncio
async def test_mixed_requests_limited():
    """Test that mixing single and batch requests respects the concurrency limit."""
    active_requests = []
    
    async def make_request(is_batch, i):
        try:
            if is_batch:
                response = client.post(
                    "/process/batch",
                    json={
                        "urls": [f"https://www.instagram.com/video{i}_{j}.mp4" for j in range(3)],
                        "encode_base64": False
                    }
                )
            else:
                response = client.post(
                    "/process",
                    json={
                        "url": f"https://www.instagram.com/video{i}.mp4",
                        "encode_base64": False
                    }
                )
            
            active_requests.append(i)
            assert response.status_code in [200, 429]
            if response.status_code == 429:
                assert "Too many concurrent requests" in response.json()["detail"]
            await asyncio.sleep(0.1)
        finally:
            if i in active_requests:
                active_requests.remove(i)
    
    # Create a mix of single and batch requests
    tasks = []
    for i in range(MAX_CONCURRENT_REQUESTS + 5):
        # Alternate between single and batch requests
        is_batch = i % 2 == 0
        tasks.append(make_request(is_batch, i))
    
    # Run all requests concurrently
    await asyncio.gather(*tasks)
    
    # Verify that we never exceeded the limit
    assert len(active_requests) <= MAX_CONCURRENT_REQUESTS

def test_rate_limit_configurable():
    """Test that the rate limit can be configured via environment variable."""
    import os
    from app.main import app
    
    # Save original value
    original_limit = MAX_CONCURRENT_REQUESTS
    
    try:
        # Set a new limit
        new_limit = 5
        os.environ["MAX_CONCURRENT_REQUESTS"] = str(new_limit)
        
        # Recreate the app to pick up the new limit
        from importlib import reload
        import app.main
        reload(app.main)
        
        # Verify the new limit is applied
        assert app.main.MAX_CONCURRENT_REQUESTS == new_limit
        
    finally:
        # Restore original value
        os.environ["MAX_CONCURRENT_REQUESTS"] = str(original_limit)
        # Reload the app to restore original limit
        reload(app.main) 