import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.request import ProcessRequest, StatusRequest
from app.models.common import ProcessingStatusEnum

client = TestClient(app)

@pytest.mark.asyncio
async def test_process_media_endpoint():
    # Simulate a POST request to /api/process (using a dummy ProcessRequest).
    dummy_request = ProcessRequest(url="https://example.com/dummy.mp4", scene_threshold=0.5, max_video_duration=60.0, description="Dummy test (async stub).", tags=["test", "stub"])
    response = client.post("/api/process", json=dummy_request.model_dump())
    assert response.status_code == 202, "Expected status 202 (Accepted) for /api/process (async stub)."
    resp_json = response.json()
    # (Stub) In a real implementation, you'd (for example) queue a task and return a real task_id.
    # For now, we expect a dummy ProcessResponse (with dummy_task_123, etc.).
    assert resp_json["task_id"] == "dummy_task_123", "Expected dummy task_id (async stub)."
    assert resp_json["url"] == dummy_request.url, "Expected dummy url (async stub)."
    assert resp_json["description"] == "Dummy processing (async stub).", "Expected dummy description (async stub)."
    assert resp_json["tags"] == ["dummy", "stub"], "Expected dummy tags (async stub)."
    assert resp_json["videos"] == [], "Expected dummy videos (async stub)."
    assert resp_json["images"] == [], "Expected dummy images (async stub)."
    assert resp_json["processing_status"]["status"] == ProcessingStatusEnum.PENDING, "Expected dummy status (async stub)."
    assert resp_json["processing_status"]["progress"] == 0.0, "Expected dummy progress (async stub)."
    assert resp_json["processing_status"]["message"] == "Processing queued (stub).", "Expected dummy message (async stub)."
    assert resp_json["processing_status"]["task_id"] == "dummy_task_123", "Expected dummy task_id (async stub)."
    assert resp_json["created_at"] is None, "Expected dummy created_at (async stub)."
    assert resp_json["completed_at"] is None, "Expected dummy completed_at (async stub)."

@pytest.mark.asyncio
async def test_check_status_endpoint():
    # Simulate a GET request to /api/status (using a dummy StatusRequest (with a dummy task_id)).
    dummy_request = StatusRequest(task_id="dummy_task_123")
    response = client.get("/api/status", params=dummy_request.model_dump())
    assert response.status_code == 200, "Expected status 200 (OK) for /api/status (async stub)."
    resp_json = response.json()
    # (Stub) In a real implementation, you'd query a database or a task queue (using dummy_request.task_id) for the status.
    # For now, we expect a dummy ProcessingStatus (with dummy_task_123, etc.).
    assert resp_json["status"] == ProcessingStatusEnum.PENDING, "Expected dummy status (async stub)."
    assert resp_json["progress"] == 0.0, "Expected dummy progress (async stub)."
    assert resp_json["message"] == "Status check (async stub).", "Expected dummy message (async stub)."
    assert resp_json["task_id"] == dummy_request.task_id, "Expected dummy task_id (async stub)."

@pytest.mark.asyncio
async def test_validation_error():
    # (Stub) Simulate a POST request to /api/process with an invalid payload (for example, missing required field "url").
    invalid_payload = {"scene_threshold": 0.5, "max_video_duration": 60.0, "description": "Dummy test (async stub).", "tags": ["test", "stub"]}
    response = client.post("/api/process", json=invalid_payload)
    assert response.status_code == 400, "Expected status 400 (Bad Request) for invalid payload (async stub)."
    resp_json = response.json()
    assert "Validation Error" in resp_json["error"], "Expected error (async stub)."