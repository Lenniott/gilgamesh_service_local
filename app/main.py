# main.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Union
import uvicorn
import os
import traceback

# Import your actual functions
from app.media_utils import process_single_url
from app.cleanup import cleanup_temp_folder
from app.stitch_scenes import stitch_scenes_to_base64
from app.downloaders import download_media_and_metadata
from app.video_processing import cleanup_temp_files

app = FastAPI(
    title="Gilgamesh Media Processing Service",
    description="Process Instagram posts, reels, and YouTube videos to extract media, text, and transcripts",
    version="1.0.0"
)

class DownloadRequest(BaseModel):
    urls: List[HttpUrl]
    encode_base64: bool = True  # Whether to include base64-encoded media in the response

class ProcessResponse(BaseModel):
    status: str
    results: List[Dict]

class ErrorResponse(BaseModel):
    status: str = "error"
    error: str
    url: Optional[str] = None

class SceneInput(BaseModel):
    video: str  # base64 string
    audio: Optional[str] = None  # optional base64 string

class StitchRequest(BaseModel):
    scenes: List[SceneInput]

@app.post("/process", response_model=ProcessResponse, responses={
    200: {"description": "Successfully processed all URLs"},
    400: {"model": ErrorResponse, "description": "Invalid request"},
    500: {"model": ErrorResponse, "description": "Server error"}
})
async def process_handler(request: DownloadRequest, background_tasks: BackgroundTasks):
    """
    Process one or more URLs (Instagram posts, reels, or YouTube videos).
    
    Each URL will be processed independently, and the response will contain results
    for all URLs, with any errors captured per-URL.
    
    Args:
        request: DownloadRequest containing:
            - urls: List of URLs to process
            - encode_base64: Whether to include base64-encoded media (default: True)
    
    The response format for each URL will be:
    {
        "url": str,
        "title": str,
        "description": str,
        "tags": List[str],
        "videos": Optional[List[Dict]],  # For posts with videos/reels
        "images": Optional[List[Dict]]   # For posts with images
    }
    """
    if not request.urls:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "error": "No URLs provided"}
        )
    
    results = []
    for url in request.urls:
        try:
            # Process each URL independently
            result = process_single_url(str(url), encode_base64=request.encode_base64)
            results.append(result)
        except Exception as e:
            # Capture error but continue processing other URLs
            error_detail = {
                "status": "error",
                "error": str(e),
                "url": str(url)
            }
            print(f"Error processing URL {url}:")
            print(traceback.format_exc())
            results.append(error_detail)
    
    return {"status": "success", "results": results}

@app.post("/cleanup")
async def cleanup_handler():
    """Clean up all temporary files."""
    try:
        cleanup_temp_folder()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "error": str(e)}
        )

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

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8500, reload=True)
