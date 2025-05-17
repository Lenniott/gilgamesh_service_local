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
from app.cache import Cache

# Initialize cache
cache = Cache(ttl_hours=24)  # 24 hour TTL

app = FastAPI(
    title="Gilgamesh Media Processing Service",
    description="Process Instagram posts, reels, and YouTube videos to extract media, text, and transcripts",
    version="1.0.0"
)

class DownloadRequest(BaseModel):
    urls: List[HttpUrl]
    encode_base64: bool = True  # Whether to include base64-encoded video data in the response
    cleanup_temp: bool = True   # Whether to clean up temporary files and cache after processing

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
            - encode_base64: Whether to include base64-encoded video data (default: True)
            - cleanup_temp: Whether to clean up temporary files and cache after processing (default: True)
    
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
    temp_dirs = []  # Keep track of temp directories for cleanup
    
    for url in request.urls:
        try:
            url_str = str(url)
            
            # Try to get from cache first
            cached_result = cache.get(url_str, encode_base64=request.encode_base64)
            if cached_result:
                results.append(cached_result)
                continue
                
            # Process URL if not in cache
            result = process_single_url(url_str, encode_base64=request.encode_base64)
            
            # Store temp directory for potential cleanup
            if 'temp_dir' in result:
                temp_dirs.append(result['temp_dir'])
                # Remove temp_dir from response
                result.pop('temp_dir', None)
            
            # Cache the result in the background
            background_tasks.add_task(cache.set, url_str, result)
            
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
    
    # Clean up temp directories and cache if requested
    if request.cleanup_temp and temp_dirs:
        background_tasks.add_task(cleanup_temp_dirs, temp_dirs, clear_cache=True)
    
    return {"status": "success", "results": results}

def cleanup_temp_dirs(temp_dirs: List[str], clear_cache: bool = False) -> None:
    """
    Clean up temporary directories and optionally clear the cache.
    
    Args:
        temp_dirs: List of temporary directories to clean up
        clear_cache: Whether to also clear the cache (default: False)
    """
    # Clean up temp directories
    for temp_dir in temp_dirs:
        try:
            cleanup_temp_files(temp_dir)
        except Exception as e:
            print(f"Error cleaning up temp directory {temp_dir}: {e}")
    
    # Clear cache if requested
    if clear_cache:
        try:
            cache.clear()
        except Exception as e:
            print(f"Error clearing cache: {e}")

@app.post("/cleanup")
async def cleanup_handler(clear_cache: bool = True):
    """
    Clean up all temporary files and optionally clear the cache.
    
    Args:
        clear_cache: Whether to also clear the cache (default: True)
    """
    try:
        # Clean up temp folder
        cleanup_temp_folder()
        
        # Clear cache if requested
        if clear_cache:
            cache.clear()
            
        return {
            "status": "success",
            "message": "Cleanup completed successfully",
            "cache_cleared": clear_cache
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error": str(e),
                "cache_cleared": False
            }
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

@app.get("/cache/stats")
async def cache_stats():
    """Get cache statistics."""
    return cache.get_stats()

@app.post("/cache/clear")
async def clear_cache(older_than_hours: Optional[int] = None):
    """
    Clear the cache.
    
    Args:
        older_than_hours: If provided, only clear entries older than this many hours
    """
    try:
        cache.clear(older_than_hours)
        return {"status": "success", "message": "Cache cleared successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "error": str(e)}
        )

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8500, reload=True)
