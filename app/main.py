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
    aspect_ratio: str = "9:16"               # "square" or "9:16"
    max_duration: float = 600.0              # 10 minutes max
    include_base64: bool = False             # Return final video in response
    audio: bool = True                       # Include base64 audio in JSON (debugging)
    clips: bool = True                       # Include base64 clips in JSON (debugging)
    text_only: bool = True                   # Default to text-only for cost reduction
    max_segments_per_video: int = 2          # Diversity control
    min_unique_videos: int = 3               # Diversity control

class QdrantIndexRequest(BaseModel):
    collections: Optional[list] = None  # Specific collections to index, or None for default
    force_rebuild: bool = False  # Whether to force full index rebuild

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
                "/vectorize/existing": "Vectorize unvectorized videos in database",
                "/qdrant/force-index": "Force indexing of Qdrant collections for AI video compilation"
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
    3. AI generates compilation JSON (script + clips + audio)
    4. Video stitcher processes JSON into final video (if include_base64=True)
    5. Saves the generated video to the database
    
    Debugging options:
    - audio=false: Skip audio generation for faster testing
    - clips=false: Skip video clip extraction for faster testing
    - include_base64=false: Skip final video composition for JSON testing
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
                aspect_ratio=request.aspect_ratio,
                max_duration=request.max_duration,
                include_base64=request.include_base64,
                audio=request.audio,
                clips=request.clips,
                text_only=request.text_only,
                max_segments_per_video=request.max_segments_per_video,
                min_unique_videos=request.min_unique_videos
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
                    "compilation_json": result.compilation_json,
                    "video_base64": result.video_base64,
                    "metadata": result.metadata
                }
            else:
                raise HTTPException(status_code=500, detail=result.error)
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Compilation failed: {str(e)}")

@app.post("/qdrant/force-index")
async def force_qdrant_indexing(request: QdrantIndexRequest):
    """
    Force indexing of Qdrant collections for AI video compilation pipeline.
    
    This endpoint triggers indexing for collections that have vectors but aren't indexed yet.
    Primarily used for the AI video compilation pipeline collections:
    - video_transcript_segments
    - video_scene_descriptions
    """
    async with semaphore:
        try:
            from app.db_connections import DatabaseConnections
            
            # Initialize database connections
            connections = DatabaseConnections()
            await connections.connect_all()
            
            if not connections.qdrant_client:
                raise HTTPException(status_code=503, detail="Qdrant client not available")
            
            # Default collections for AI video compilation
            default_collections = ["video_transcript_segments", "video_scene_descriptions"]
            target_collections = request.collections or default_collections
            
            results = {}
            overall_success = True
            
            for collection_name in target_collections:
                try:
                    # Get collection status before indexing
                    try:
                        collection_info = connections.qdrant_client.get_collection(collection_name)
                        points_before = collection_info.points_count
                        indexed_before = getattr(collection_info, 'indexed_vectors_count', 0)
                    except Exception:
                        results[collection_name] = {
                            "success": False,
                            "error": f"Collection '{collection_name}' does not exist"
                        }
                        overall_success = False
                        continue
                    
                    # Force indexing by updating collection optimization settings
                    from qdrant_client.models import OptimizersConfigDiff
                    
                    if request.force_rebuild:
                        # Force full index rebuild by temporarily changing optimization settings
                        connections.qdrant_client.update_collection(
                            collection_name=collection_name,
                            optimizer_config=OptimizersConfigDiff(
                                indexing_threshold=1  # Force immediate indexing
                            )
                        )
                        
                        # Wait a moment for the change to take effect
                        await asyncio.sleep(1)
                        
                        # Restore default settings
                        connections.qdrant_client.update_collection(
                            collection_name=collection_name,
                            optimizer_config=OptimizersConfigDiff(
                                indexing_threshold=20000  # Back to default
                            )
                        )
                    else:
                        # Trigger optimization which forces indexing
                        connections.qdrant_client.update_collection(
                            collection_name=collection_name,
                            optimizer_config=OptimizersConfigDiff(
                                indexing_threshold=1  # Force immediate indexing
                            )
                        )
                    
                    # Wait for indexing to complete
                    await asyncio.sleep(2)
                    
                    # Get collection status after indexing
                    collection_info_after = connections.qdrant_client.get_collection(collection_name)
                    points_after = collection_info_after.points_count
                    indexed_after = getattr(collection_info_after, 'indexed_vectors_count', 0)
                    
                    results[collection_name] = {
                        "success": True,
                        "before": {
                            "points_count": points_before,
                            "indexed_vectors_count": indexed_before
                        },
                        "after": {
                            "points_count": points_after,
                            "indexed_vectors_count": indexed_after
                        },
                        "indexing_triggered": indexed_after > indexed_before,
                        "force_rebuild": request.force_rebuild
                    }
                    
                except Exception as e:
                    results[collection_name] = {
                        "success": False,
                        "error": str(e)
                    }
                    overall_success = False
            
            # Clean up connections
            await connections.close_all()
            
            return {
                "success": overall_success,
                "message": f"Indexing {'completed' if overall_success else 'partially completed'} for {len(target_collections)} collections",
                "collections_processed": target_collections,
                "force_rebuild": request.force_rebuild,
                "results": results,
                "next_steps": {
                    "test_search": "Use /search endpoint to test if search now works",
                    "ai_compilation": "Try the AI video compilation pipeline",
                    "verify_indexing": "Check that indexed_vectors_count > 0 for your collections"
                }
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Qdrant indexing failed: {str(e)}")

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
            "enhanced_video_context": True,
            "rate_limiting": True
        }
    }

@app.get("/rate-limits")
async def get_rate_limits():
    """Get current rate limiting status for all AI providers."""
    try:
        from app.ai_rate_limiter import get_all_usage_stats
        usage_stats = get_all_usage_stats()
        
        return {
            "success": True,
            "providers": usage_stats,
            "message": "Rate limiting statistics retrieved successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get rate limiting statistics: {str(e)}",
            "providers": {}
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8500))
    uvicorn.run(app, host="0.0.0.0", port=port)
