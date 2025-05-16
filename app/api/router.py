from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError
from app.models.request import ProcessRequest, StatusRequest
from app.models.response import ProcessResponse, ProcessingStatus, ErrorResponse
from app.models.common import ProcessingStatusEnum

router = APIRouter(prefix="/api", tags=["media"])

@router.post("/process", response_model=ProcessResponse, status_code=status.HTTP_202_ACCEPTED, summary="Process a single media URL (async stub).")
async def process_media(request: ProcessRequest) -> ProcessResponse:
    # (Stub) In a real implementation, you'd queue a background task (or call a service) to process the media.
    # For now, we return a dummy ProcessResponse.
    dummy_response = ProcessResponse(
        task_id="dummy_task_123",
        url=request.url,
        description="Dummy processing (async stub).",
        tags=["dummy", "stub"],
        videos=[],
        images=[],
        processing_status=ProcessingStatus(status=ProcessingStatusEnum.PENDING, progress=0.0, message="Processing queued (stub).", task_id="dummy_task_123"),
        created_at=None,  # (In a real endpoint, you'd set this to datetime.utcnow.)
        completed_at=None
    )
    return dummy_response

@router.get("/status", response_model=ProcessingStatus, status_code=status.HTTP_200_OK, summary="Check processing status (async stub).")
async def check_status(request: StatusRequest) -> ProcessingStatus:
    # (Stub) In a real implementation, you'd query a database or a task queue for the status of the task (using request.task_id).
    # For now, we return a dummy ProcessingStatus.
    dummy_status = ProcessingStatus(
        status=ProcessingStatusEnum.PENDING,
        progress=0.0,
        message="Status check (async stub).",
        task_id=request.task_id
    )
    return dummy_status

# (Optional) Add a catch-all error handler (for example, if a ValidationError is raised by FastAPI) to return a standardized ErrorResponse.
@router.exception_handler(ValidationError)
async def validation_exception_handler(request, exc: ValidationError):
    error_detail = "Invalid request payload."
    if exc.errors():
        error_detail = str(exc.errors())
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ErrorResponse(error="Validation Error", detail=error_detail, status_code=status.HTTP_400_BAD_REQUEST).model_dump()) 