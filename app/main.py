# main.py
from fastapi import FastAPI, HTTPException, status, Request
from pydantic import BaseModel, ValidationError
from typing import List, Optional
import uvicorn
import os
from app.api import router
from fastapi.middleware.cors import CORSMiddleware
from app.core.errors import ProcessingError
from app.models.response import ErrorResponse
import logging
import logging.handlers

# Import your actual functions
from app.media_utils import process_url, process_and_cleanup
from app.cleanup import cleanup_temp_folder
from app.stitch_scenes import stitch_scenes_to_base64
from app.downloaders import download_media_and_metadata
from app.video_processing import cleanup_temp_files

# Configure logging
def setup_logging():
    """Configure logging for the application."""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # Console handler
            logging.StreamHandler(),
            # File handler with rotation
            logging.handlers.RotatingFileHandler(
                'logs/app.log',
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
        ]
    )
    
    # Set specific log levels for different modules
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('fastapi').setLevel(logging.WARNING)
    
    # Create logger for this module
    logger = logging.getLogger(__name__)
    logger.info("Logging configured successfully")

app = FastAPI(
    title="Gilgamesh Media Processing Service",
    description="Process Instagram and YouTube media to extract videos, images, text, and transcripts",
    version="1.0.0"
)

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    return {
        "message": "Welcome to Gilgamesh Media Processing Service",
        "endpoints": {
            "/api/process": "POST - Process Instagram and YouTube media URLs",
            "example": {
                "urls": [
                    "https://www.instagram.com/p/DJpP_JPSKHK/?igsh=MmIyb2twNXc0ajNv",
                    "https://youtube.com/shorts/izeO1Vpqvvo?si=blnnaTO0uYEe5htC"
                ]
            }
        }
    }

class DownloadRequest(BaseModel):
    urls: List[str]

class SceneInput(BaseModel):
    video: str  # base64 string
    audio: Optional[str] = None  # optional base64 string

class StitchRequest(BaseModel):
    scenes: List[SceneInput]

@app.post("/process")
def download_handler(request: DownloadRequest):
    try:
        results = []
        for url in request.urls:
            try:
                result = process_and_cleanup(url)
                results.append(result)
            except Exception as e:
                import traceback
                print("Error processing URL:", url)
                print("Error details:", str(e))
                print("Traceback:")
                print(traceback.format_exc())
                raise HTTPException(status_code=500, detail=f"Error processing URL {url}: {str(e)}")
        
        return {"status": "success", "results": results}
    except Exception as e:
        import traceback
        print("Error in download_handler:")
        print("Error details:", str(e))
        print("Traceback:")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cleanup")
def cleanup_handler():
    try:
        cleanup_temp_folder()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/download")
def download_media_and_metadata(url: str):
    try:
        result = download_media_and_metadata(url)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stitch")
def stitch_handler(request: StitchRequest):
    try:
        # Stitch the scenes and get base64 output
        base64_output = stitch_scenes_to_base64(request.scenes)
        
        return {
            "status": "success",
            "video": base64_output,
            "message": "Video successfully stitched"
        }
    except Exception as e:
        import traceback
        print("Error in stitch_handler:")
        print("Error details:", str(e))
        print("Traceback:")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# Include our router which defines the /api/process endpoint
app.include_router(router)

@app.exception_handler(ProcessingError)
async def processing_error_handler(request: Request, exc: ProcessingError):
    """Handle processing errors and return appropriate response."""
    logger.error(f"Processing error: {str(exc)}", exc_info=True)
    return ErrorResponse(
        error="Processing Error",
        detail=str(exc),
        status_code=500
    ).model_dump()

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions and return appropriate response."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return ErrorResponse(
        error="Internal Server Error",
        detail="An unexpected error occurred",
        status_code=500
    ).model_dump()

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    error_detail = "Invalid request payload."
    if exc.errors():
        error_detail = str(exc.errors())
    logger.error(f"Validation error: {error_detail}", exc_info=True)
    return ErrorResponse(
        error="Validation Error",
        detail=error_detail,
        status_code=400
    ).model_dump()

@app.on_event("startup")
async def startup_event():
    """Log startup event."""
    logger.info("Media Processing Service starting up")

@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown event."""
    logger.info("Media Processing Service shutting down")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8500, reload=True)
