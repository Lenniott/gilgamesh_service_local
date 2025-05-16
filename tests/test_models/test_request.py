import pytest
from app.models.request import ProcessRequest, BatchProcessRequest, StatusRequest

def test_process_request():
    # Test valid request
    request = ProcessRequest(
        url="https://example.com/video.mp4",
        include_video_base64=True,
        scene_threshold=0.3,
        max_video_duration=300,
        language="en"
    )
    assert str(request.url) == "https://example.com/video.mp4"
    assert request.include_video_base64 is True
    assert request.scene_threshold == 0.3
    assert request.max_video_duration == 300
    assert request.language == "en"

    # Test invalid scene threshold
    with pytest.raises(ValueError):
        ProcessRequest(
            url="https://example.com/video.mp4",
            scene_threshold=1.5
        )

    # Test invalid max duration
    with pytest.raises(ValueError):
        ProcessRequest(
            url="https://example.com/video.mp4",
            max_video_duration=0
        )

def test_batch_process_request():
    # Test valid request
    request = BatchProcessRequest(
        urls=[
            "https://example.com/video1.mp4",
            "https://example.com/video2.mp4"
        ],
        include_video_base64=True,
        scene_threshold=0.3,
        max_video_duration=300,
        language="en",
        parallel_processing=True
    )
    assert len(request.urls) == 2
    assert str(request.urls[0]) == "https://example.com/video1.mp4"
    assert str(request.urls[1]) == "https://example.com/video2.mp4"
    assert request.include_video_base64 is True
    assert request.scene_threshold == 0.3
    assert request.max_video_duration == 300
    assert request.language == "en"
    assert request.parallel_processing is True

    # Test duplicate URLs
    with pytest.raises(ValueError):
        BatchProcessRequest(
            urls=[
                "https://example.com/video.mp4",
                "https://example.com/video.mp4"
            ]
        )

    # Test too many URLs
    with pytest.raises(ValueError):
        BatchProcessRequest(
            urls=["https://example.com/video.mp4"] * 11
        )

    # Test no URLs
    with pytest.raises(ValueError):
        BatchProcessRequest(
            urls=[]
        )

def test_status_request():
    # Test valid request
    request = StatusRequest(task_id="task_123")
    assert request.task_id == "task_123"

    # Test empty task ID
    with pytest.raises(ValueError):
        StatusRequest(task_id="")

def test_process_request_url_validation():
    # Valid URL
    req = ProcessRequest(url="https://valid.com/video.mp4")
    assert str(req.url) == "https://valid.com/video.mp4"
    # Invalid URL
    with pytest.raises(ValueError):
        ProcessRequest(url="not-a-url")

def test_batch_process_request_url_validation():
    # Valid URLs
    req = BatchProcessRequest(urls=["https://a.com/1", "https://b.com/2"])
    assert len(req.urls) == 2
    # Duplicate URLs
    with pytest.raises(ValueError):
        BatchProcessRequest(urls=["https://a.com/1", "https://a.com/1"])
    # Too many URLs
    with pytest.raises(ValueError):
        BatchProcessRequest(urls=[f"https://a.com/{i}" for i in range(11)])

def test_process_request_serialization():
    req = ProcessRequest(url="https://valid.com/video.mp4", scene_threshold=0.5)
    data = req.model_dump()
    assert str(data["url"]) == "https://valid.com/video.mp4"
    assert data["scene_threshold"] == 0.5

def test_batch_process_request_serialization():
    req = BatchProcessRequest(urls=["https://a.com/1"], scene_threshold=0.3)
    data = req.model_dump()
    assert [str(u) for u in data["urls"]] == ["https://a.com/1"]
    assert data["scene_threshold"] == 0.3 