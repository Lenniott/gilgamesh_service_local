# main.py
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Union
import uvicorn
import os
import traceback
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import your actual functions
from app.media_utils import process_single_url, process_and_cleanup
from app.cleanup import cleanup_temp_folder
from app.stitch_scenes import stitch_scenes_to_base64
from app.downloaders import download_media_and_metadata
from app.video_processing import cleanup_temp_files
from app.cache import Cache
from app.utils import is_valid_url

# Initialize cache
cache = Cache(ttl_hours=24)  # 24 hour TTL

app = FastAPI(
    title="Gilgamesh Media Processing Service",
    description="Process Instagram posts, reels, and YouTube videos to extract media, text, and transcripts",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class URLRequest(BaseModel):
    url: HttpUrl
    cleanup_temp: bool = True
    threshold: float = 0.22
    encode_base64: bool = True

class URLBatchRequest(BaseModel):
    urls: List[HttpUrl]
    cleanup_temp: bool = True
    threshold: float = 0.22

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

@app.post("/process")
async def process_handler(request: URLRequest, background_tasks: BackgroundTasks) -> Dict:
    """
    Process a single URL and return the result.
    Optionally clean up temporary files after processing.
    """
    if not is_valid_url(str(request.url)):
        raise HTTPException(status_code=400, detail="Unsupported URL")
        
    try:
        result = await process_single_url(str(request.url), request.threshold, request.encode_base64)
        
        if request.cleanup_temp:
            background_tasks.add_task(cleanup_temp_folder, result['temp_dir'])
            
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process/batch")
async def process_batch_handler(request: URLBatchRequest, background_tasks: BackgroundTasks) -> Dict:
    """
    Process multiple URLs concurrently and return the results.
    Optionally clean up temporary files after processing.
    """
    results = []
    errors = []
    
    # Process URLs concurrently
    async def process_url(url: str) -> Dict:
        try:
            if not is_valid_url(url):
                return {"status": "error", "url": url, "detail": "Unsupported URL"}
                
            result = await process_single_url(url, request.threshold, request.encode_base64)
            
            if request.cleanup_temp:
                background_tasks.add_task(cleanup_temp_folder, result['temp_dir'])
                
            return {"status": "success", "url": url, "result": result}
        except Exception as e:
            return {"status": "error", "url": url, "detail": str(e)}
    
    # Process all URLs concurrently
    tasks = [process_url(str(url)) for url in request.urls]
    responses = await asyncio.gather(*tasks)
    
    # Split responses into results and errors
    for response in responses:
        if response["status"] == "success":
            results.append(response)
        else:
            errors.append(response)
    
    return {
        "status": "success",
        "results": results,
        "errors": errors
    }

@app.post("/cleanup")
async def cleanup_handler(clear_cache_data: bool = False) -> Dict:
    """
    Clean up temporary files and optionally clear the cache.
    """
    try:
        await asyncio.to_thread(cleanup_temp_folder)
        if clear_cache_data:
            await asyncio.to_thread(cache.clear)
        return {"status": "success", "message": "Cleanup completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cache/stats")
async def cache_stats_handler() -> Dict:
    """
    Get cache statistics.
    """
    try:
        stats = await asyncio.to_thread(cache.get_stats)
        return {"status": "success", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cache/clear")
async def clear_cache_handler() -> Dict:
    """
    Clear the cache.
    """
    try:
        await asyncio.to_thread(cache.clear)
        return {"status": "success", "message": "Cache cleared"}
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

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8500, reload=True)
