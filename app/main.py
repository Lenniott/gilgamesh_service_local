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
from app.video_compilation_pipeline import get_compilation_pipeline, CompilationRequest, CompilationResponse

app = FastAPI(
    title="Gilgamesh Media Processing Service",
    description="Process Instagram posts, reels, and YouTube videos with AI scene analysis and transcript integration. Supports Instagram carousels with multiple videos.",
    version="2.2.12"
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

class ProcessRequest(BaseModel):
    url: HttpUrl
    save_video: bool = True
    transcribe: bool = True
    describe: bool = True
    save_to_postgres: bool = True
    save_to_qdrant: bool = True
    include_base64: bool = False
    raw_transcript: bool = False  # Return raw text without timestamps

class CarouselRequest(BaseModel):
    url: HttpUrl
    include_base64: bool = False

class VectorizeExistingRequest(BaseModel):
    limit: Optional[int] = None
    dry_run: bool = False
    verbose: bool = False

class CompileRequest(BaseModel):
    context: str                              # "I'm creating a morning workout routine"
    requirements: str                         # "5 minutes, beginner-friendly, mobility focus"
    title: Optional[str] = None              # "Morning Mobility Routine"
    voice_preference: str = "alloy"          # OpenAI TTS voice
    resolution: str = "720p"                 # Output resolution
    max_duration: float = 600.0              # 10 minutes max
    include_base64: bool = False             # Return video in response

@app.get("/")
async def root():
    return {
        "message": "Gilgamesh Media Processing Service",
        "version": "2.2.12",
        "features": [
            "Instagram carousel support",
            "Smart AI credit management",
            "Enhanced video context analysis",
            "Graceful audio handling",
            "Multi-video processing"
        ],
        "endpoints": {
            "process": {
                "/process": "Main processing endpoint with all options - checks if URL already processed"
            },
            "compilation": {
                "/compile": "AI-powered video compilation - create new videos from existing content"
            },
            "vectorization": {
                "/vectorize/existing": "Vectorize unvectorized videos in database"
            },
            "retrieval": {
                "/video/{video_id}": "Get specific video by ID",
                "/carousel": "Get all videos from carousel URL",
                "/search": "Search videos by content",
                "/videos": "List recent videos"
            },
            "generated": {
                "/generated/{video_id}": "Get generated video by ID",
                "/generated/search": "Search generated videos",
                "/generated/recent": "List recent generated videos"
            }
        }
    }

@app.post("/process")
async def process_video(request: ProcessRequest):
    """
    Main video processing endpoint with all options.
    Automatically checks if URL has already been processed to save AI credits.
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
                save_to_postgres=request.save_to_postgres,
                save_to_qdrant=request.save_to_qdrant,
                include_base64=request.include_base64
            )
            
            # Post-process for raw transcript if requested
            if request.raw_transcript and result["success"]:
                for video in result.get("videos", []):
                    transcript_data = video.get("results", {}).get("transcript_data")
                    if transcript_data:
                        # Convert timestamped segments to raw text
                        raw_text = ' '.join([segment['text'].strip() for segment in transcript_data])
                        video["results"]["raw_transcript"] = raw_text
            
            if result["success"]:
                return result
            else:
                raise HTTPException(status_code=500, detail=result.get("error", "Processing failed"))
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/vectorize/existing")
async def vectorize_existing_videos(request: VectorizeExistingRequest):
    """
    Vectorize existing videos in the database that haven't been vectorized yet.
    Creates individual vector points for each transcript segment and scene description.
    """
    async with semaphore:
        try:
            # Import the vectorization class
            import sys
            import os
            
            # Import the vectorization class from the app module
            from app.vectorization import VectorizeExistingVideos
            
            # Create vectorizer instance
            vectorizer = VectorizeExistingVideos()
            
            try:
                # Initialize database connections
                await vectorizer.initialize()
                
                # Run vectorization with provided parameters
                result = await vectorizer.vectorize_all_unvectorized(
                    limit=request.limit,
                    dry_run=request.dry_run
                )
                
                # Enhanced response with detailed information
                response = {
                    "success": result["success"],
                    "message": result["message"],
                    "parameters": {
                        "limit": request.limit,
                        "dry_run": request.dry_run,
                        "verbose": request.verbose
                    },
                    "results": {
                        "total_videos": result.get("total_videos", 0),
                        "processed": result.get("processed", 0),
                        "successful": result.get("successful", 0),
                        "failed": result.get("failed", 0)
                    }
                }
                
                # Add error details if present
                if "error" in result:
                    response["error"] = result["error"]
                
                # Add video details for dry run
                if request.dry_run and "videos" in result:
                    response["videos_to_process"] = [
                        {
                            "video_id": video["id"],
                            "url": video["url"],
                            "carousel_index": video.get("carousel_index", 0),
                            "has_transcript": bool(video.get("transcript")),
                            "has_descriptions": bool(video.get("descriptions")),
                            "created_at": str(video["created_at"])
                        }
                        for video in result["videos"]
                    ]
                
                return response
                
            finally:
                # Always cleanup connections
                await vectorizer.cleanup()
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Vectorization failed: {str(e)}")

@app.post("/compile")
async def compile_video(request: CompileRequest):
    """
    AI-powered video compilation endpoint.
    Creates new videos from existing content based on user requirements.
    
    This endpoint:
    1. Analyzes user context and requirements
    2. Searches existing video database for relevant content
    3. Generates a structured script with video assignments
    4. Creates audio narration using OpenAI TTS
    5. Composes final video with synchronized audio and video segments
    6. Saves the generated video to the database
    """
    async with semaphore:
        try:
            # Get compilation pipeline
            pipeline = await get_compilation_pipeline()
            
            # Convert request to internal format
            compilation_request = CompilationRequest(
                context=request.context,
                requirements=request.requirements,
                title=request.title,
                voice_preference=request.voice_preference,
                resolution=request.resolution,
                max_duration=request.max_duration,
                include_base64=request.include_base64
            )
            
            # Process the compilation request
            result = await pipeline.process_compilation_request(compilation_request)
            
            if result.success:
                return {
                    "success": True,
                    "generated_video_id": result.generated_video_id,
                    "duration": result.duration,
                    "source_videos_used": result.source_videos_used,
                    "processing_time": result.processing_time,
                    "script": result.script,
                    "video_base64": result.video_base64,
                    "metadata": result.metadata
                }
            else:
                raise HTTPException(status_code=500, detail=result.error)
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Compilation failed: {str(e)}")

@app.get("/generated/{video_id}")
async def get_generated_video(video_id: str, include_base64: bool = False):
    """Get generated video by ID - follows existing /video/{video_id} pattern."""
    try:
        # Get compilation pipeline to access generated video database
        pipeline = await get_compilation_pipeline()
        
        # Get generated video
        video_data = await pipeline.generated_video_db.get_generated_video(
            video_id, include_base64
        )
        
        if video_data:
            return {
                "success": True,
                "video": video_data
            }
        else:
            raise HTTPException(status_code=404, detail="Generated video not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get generated video: {str(e)}")

@app.get("/generated/search")  
async def search_generated_videos(q: str, duration_min: Optional[float] = None, 
                                 duration_max: Optional[float] = None,
                                 resolution: Optional[str] = None,
                                 voice_model: Optional[str] = None,
                                 limit: int = 10):
    """Search generated videos - follows existing /search pattern."""
    try:
        # Get compilation pipeline to access generated video database
        pipeline = await get_compilation_pipeline()
        
        # Search generated videos
        results = await pipeline.generated_video_db.search_generated_videos(
            query=q,
            duration_min=duration_min,
            duration_max=duration_max,
            resolution=resolution,
            voice_model=voice_model,
            limit=limit
        )
        
        return {
            "success": True,
            "query": q,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/generated/recent")
async def list_recent_generated_videos(limit: int = 20):
    """List recent generated videos - follows existing /videos pattern."""
    try:
        # Get compilation pipeline to access generated video database
        pipeline = await get_compilation_pipeline()
        
        # List recent generated videos
        results = await pipeline.generated_video_db.list_recent_generated_videos(limit)
        
        return {
            "success": True,
            "videos": results,
            "count": len(results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list generated videos: {str(e)}")

@app.get("/compile/status/{compilation_id}")
async def get_compilation_status(compilation_id: str):
    """Get compilation status for long-running generations."""
    try:
        # Get compilation pipeline
        pipeline = await get_compilation_pipeline()
        
        # Get compilation status
        status = await pipeline.get_compilation_status(compilation_id)
        
        return {
            "success": True,
            "status": status
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get compilation status: {str(e)}")

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
        "version": "2.2.12",
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
