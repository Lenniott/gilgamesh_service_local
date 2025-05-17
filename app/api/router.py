from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import ValidationError
from app.models.request import ProcessRequest, StatusRequest
from app.models.response import ProcessResponse, ProcessingStatus, ErrorResponse, BatchProcessResponse
from app.models.common import ProcessingStatusEnum
from app.services.media import process_media_url
from typing import List, Dict
import asyncio
import time
from datetime import datetime, timedelta

# Rate limiting setup
RATE_LIMIT_WINDOW = 60  # 1 minute window
MAX_REQUESTS_PER_WINDOW = 30  # 30 requests per minute
rate_limit_store: Dict[str, List[float]] = {}

def get_rate_limit_key(ip: str) -> str:
    """Get rate limit key for an IP address."""
    return f"rate_limit:{ip}"

def check_rate_limit(ip: str) -> bool:
    """Check if a request is within rate limits."""
    now = time.time()
    key = get_rate_limit_key(ip)
    
    # Clean up old timestamps
    if key in rate_limit_store:
        rate_limit_store[key] = [ts for ts in rate_limit_store[key] if now - ts < RATE_LIMIT_WINDOW]
    
    # Check if we're over the limit
    if key in rate_limit_store and len(rate_limit_store[key]) >= MAX_REQUESTS_PER_WINDOW:
        return False
    
    # Add new timestamp
    if key not in rate_limit_store:
        rate_limit_store[key] = []
    rate_limit_store[key].append(now)
    
    return True

async def rate_limit_middleware(request: Request) -> None:
    """Middleware to enforce rate limiting."""
    client_ip = request.client.host
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error="Rate limit exceeded",
                detail=f"Too many requests. Maximum {MAX_REQUESTS_PER_WINDOW} requests per {RATE_LIMIT_WINDOW} seconds.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS
            ).model_dump()
        )

router = APIRouter(prefix="/api", tags=["media"])

@router.post("/process", response_model=BatchProcessResponse, status_code=status.HTTP_200_OK, dependencies=[Depends(rate_limit_middleware)])
async def process_media(request: ProcessRequest) -> BatchProcessResponse:
    """
    Process multiple media URLs (Instagram posts, carousels, reels, or YouTube shorts).
    Returns processed results including videos, images, text, and transcripts.
    
    Optional parameters:
    - scene_threshold: Threshold for scene detection (0.0 to 1.0, higher = more sensitive)
    - include_video_base64: Whether to include base64-encoded videos in response
    - max_video_duration: Maximum video duration to process in seconds
    - language: Language code for transcription (e.g., 'en', 'es')
    
    Rate limiting:
    - Maximum 30 requests per minute per IP address
    """
    try:
        # Process all URLs concurrently with the same request parameters
        tasks = [process_media_url(url, request) for url in request.urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out any failed results and convert exceptions to error responses
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                # Log the error but continue processing other URLs
                print(f"Error processing URL: {str(result)}")
                continue
            processed_results.append(result)
        
        if not processed_results:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="All URLs failed to process"
            )
        
        return BatchProcessResponse(results=processed_results)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

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