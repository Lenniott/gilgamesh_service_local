# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict
import uvicorn
import os
import asyncio
from fastapi.middleware.cors import CORSMiddleware

# Import your actual functions
from app.simple_unified_processor import process_video_unified_simple, get_carousel_videos
from app.utils import is_valid_url

app = FastAPI(
    title="Gilgamesh Media Processing Service",
    description="Process Instagram posts, reels, and YouTube videos with AI scene analysis and transcript integration. Supports Instagram carousels with multiple videos.",
    version="2.2.2"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Concurrency control
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", 10))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", 30))
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

class UnifiedProcessRequest(BaseModel):
    url: HttpUrl
    save: bool = False
    transcribe: Optional[str] = None  # None, "raw", or "timestamp"
    describe: bool = False
    save_to_postgres: bool = True
    save_to_qdrant: bool = True

class SimpleProcessRequest(BaseModel):
    url: HttpUrl
    save_video: bool = True
    transcribe: bool = True
    describe: bool = True
    include_base64: bool = False

class FullProcessRequest(BaseModel):
    url: HttpUrl

class TranscriptOnlyRequest(BaseModel):
    url: HttpUrl

class QdrantOnlyRequest(BaseModel):
    url: HttpUrl

class CarouselRequest(BaseModel):
    url: HttpUrl
    include_base64: bool = False

@app.get("/")
async def root():
    return {
        "message": "Gilgamesh Media Processing Service",
        "version": "2.2.2",
        "features": [
            "Instagram carousel support",
            "Smart AI credit management",
            "Enhanced video context analysis",
            "Graceful audio handling",
            "Multi-video processing"
        ],
        "endpoints": {
            "process": {
                "/process/simple": "Flexible processing with all options",
                "/process/full": "Complete processing (save, transcribe, describe)",
                "/process/transcript-only": "Raw transcript extraction only",
                "/process/qdrant-only": "Vector database storage only",
                "/process/carousel": "Get all videos from carousel URL"
            },
            "retrieval": {
                "/video/{video_id}": "Get specific video by ID",
                "/carousel/{url}": "Get all videos from carousel URL",
                "/search": "Search videos by content",
                "/videos": "List recent videos"
            }
        }
    }

@app.post("/process/simple")
async def process_simple(request: SimpleProcessRequest):
    """
    Flexible video processing with all options.
    Supports Instagram carousels - processes all videos in carousel.
    """
    async with semaphore:
        try:
            url = str(request.url)
            if not is_valid_url(url):
                raise HTTPException(status_code=400, detail="Invalid URL format")
            
            result = await process_video_unified_simple(
                url=url,
                save_video=request.save_video,
                transcribe=request.transcribe,
                describe=request.describe,
                include_base64=request.include_base64
            )
            
            if result["success"]:
                return result
            else:
                raise HTTPException(status_code=500, detail=result.get("error", "Processing failed"))
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/process/full")
async def process_full(request: FullProcessRequest):
    """
    Complete processing: Download, save, transcribe, describe, save to PostgreSQL.
    Supports Instagram carousels - processes all videos in carousel.
    """
    async with semaphore:
        try:
            url = str(request.url)
            if not is_valid_url(url):
                raise HTTPException(status_code=400, detail="Invalid URL format")
            
            result = await process_video_unified_simple(
                url=url,
                save_video=True,
                transcribe=True,
                describe=True,
                include_base64=False
            )
            
            if result["success"]:
                return result
            else:
                raise HTTPException(status_code=500, detail=result.get("error", "Processing failed"))
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/process/transcript-only")
async def process_transcript_only(request: TranscriptOnlyRequest):
    """
    Raw transcript extraction only - no database storage.
    Supports Instagram carousels - processes all videos in carousel.
    """
    async with semaphore:
        try:
            url = str(request.url)
            if not is_valid_url(url):
                raise HTTPException(status_code=400, detail="Invalid URL format")
            
            result = await process_video_unified_simple(
                url=url,
                save_video=False,
                transcribe=True,
                describe=False,
                include_base64=False
            )
            
            if result["success"]:
                # Extract only transcript data for clean response
                transcript_data = []
                for video in result.get("videos", []):
                    video_transcript = video.get("results", {}).get("transcript_data")
                    if video_transcript:
                        transcript_data.append({
                            "carousel_index": video.get("carousel_index", 0),
                            "transcript": video_transcript
                        })
                
                return {
                    "success": True,
                    "url": url,
                    "carousel_info": result.get("carousel_info", {}),
                    "transcript_data": transcript_data
                }
            else:
                raise HTTPException(status_code=500, detail=result.get("error", "Processing failed"))
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/process/qdrant-only")
async def process_qdrant_only(request: QdrantOnlyRequest):
    """
    Vector database storage only - transcribe and save to Qdrant without video storage.
    Processes videos, generates transcripts and descriptions, but only stores to Qdrant.
    """
    async with semaphore:
        try:
            url = str(request.url)
            if not is_valid_url(url):
                raise HTTPException(status_code=400, detail="Invalid URL format")
            
            # Import the full unified processor
            from app.simple_unified_processor import process_video_unified_full
            
            result = await process_video_unified_full(
                url=url,
                save_video=False,  # Don't save video base64
                transcribe=True,   # Generate transcript for embeddings
                describe=True,     # Generate descriptions for embeddings
                save_to_postgres=False,  # Don't save to PostgreSQL
                save_to_qdrant=True,     # Only save to Qdrant
                include_base64=False
            )
            
            if result["success"]:
                return result
            else:
                raise HTTPException(status_code=500, detail=result.get("error", "Processing failed"))
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/process/carousel")
async def get_carousel(request: CarouselRequest):
    """
    Get all videos from a carousel URL.
    Retrieves existing processed videos from database.
    """
    try:
        url = str(request.url)
        if not is_valid_url(url):
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        result = await get_carousel_videos(url, request.include_base64)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=404, detail=result.get("error", "No videos found"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get carousel: {str(e)}")

# Legacy endpoint for backward compatibility
@app.post("/process/unified")
async def process_unified(request: UnifiedProcessRequest):
    """
    Legacy unified processing endpoint (backward compatibility).
    Supports Instagram carousels - processes all videos in carousel.
    Now with full PostgreSQL and Qdrant support!
    """
    async with semaphore:
        try:
            url = str(request.url)
            if not is_valid_url(url):
                raise HTTPException(status_code=400, detail="Invalid URL format")
            
            # Map legacy parameters to new system
            save_video = request.save
            transcribe = request.transcribe is not None
            describe = request.describe
            
            # Import the full unified processor
            from app.simple_unified_processor import process_video_unified_full
            
            result = await process_video_unified_full(
                url=url,
                save_video=save_video,
                transcribe=transcribe,
                describe=describe,
                save_to_postgres=request.save_to_postgres,
                save_to_qdrant=request.save_to_qdrant,
                include_base64=False
            )
            
            if result["success"]:
                return result
            else:
                raise HTTPException(status_code=500, detail=result.get("error", "Processing failed"))
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/video/{video_id}")
async def get_video(video_id: str, include_base64: bool = False):
    """Get video data by ID."""
    try:
        from app.simple_unified_processor import get_video_simple
        result = await get_video_simple(video_id, include_base64)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=404, detail=result.get("error", "Video not found"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get video: {str(e)}")

@app.get("/carousel")
async def get_carousel_by_url(url: str, include_base64: bool = False):
    """Get all videos from a carousel by URL (query parameter)."""
    try:
        if not is_valid_url(url):
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        result = await get_carousel_videos(url, include_base64)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=404, detail=result.get("error", "No videos found"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get carousel: {str(e)}")

@app.get("/search")
async def search_videos(q: str, limit: int = 10):
    """Search videos by content."""
    try:
        from app.simple_unified_processor import search_videos_simple
        result = await search_videos_simple(q, limit)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Search failed"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/videos")
async def list_videos(limit: int = 20):
    """List recent videos."""
    try:
        from app.simple_unified_processor import list_videos_simple
        result = await list_videos_simple(limit)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to list videos"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list videos: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.2.2",
        "features": {
            "carousel_support": True,
            "ai_credit_management": True,
            "graceful_audio_handling": True,
            "enhanced_video_context": True
        }
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8500))
    uvicorn.run(app, host="0.0.0.0", port=port)
