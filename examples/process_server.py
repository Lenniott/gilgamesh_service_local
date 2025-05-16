import asyncio
import json
import os
from aiohttp import web
from app.services.scene_processing import SceneProcessingService
from app.services.download import AsyncDownloadService
from app.core.errors import ProcessingError

# Store active processing tasks
active_tasks = {}

async def process_video(url: str, task_id: str) -> None:
    """Process a video asynchronously and store results."""
    try:
        # Initialize services
        download_service = AsyncDownloadService()
        scene_service = SceneProcessingService(
            threshold=0.22,
            target_width=640,
            target_bitrate="800k"
        )
        
        # Update task status
        active_tasks[task_id] = {
            "status": "downloading",
            "progress": 0,
            "url": url
        }
        
        # Download video
        download_result = await download_service.download_media(url)
        if not download_result.files:
            raise ProcessingError("No files found in download result")
            
        # Get the first video file
        video_files = [f for f in download_result.files if f.lower().endswith(('.mp4', '.mkv', '.webm'))]
        if not video_files:
            raise ProcessingError("No video files found in download result")
            
        video_path = video_files[0]
        
        # Update status
        active_tasks[task_id].update({
            "status": "processing",
            "progress": 50,
            "video_path": video_path
        })
        
        # Process video
        result = await scene_service.process_video(video_path)
        
        # Save results
        output_path = os.path.join(os.path.dirname(video_path), "scenes.json")
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
            
        # Update final status
        active_tasks[task_id].update({
            "status": "complete",
            "progress": 100,
            "result": {
                "scenes": len(result["scenes"]),
                "metadata": result["metadata"],
                "output_path": output_path
            }
        })
        
    except Exception as e:
        active_tasks[task_id].update({
            "status": "error",
            "error": str(e)
        })
        raise
    finally:
        # Cleanup after 1 hour
        await asyncio.sleep(3600)
        if task_id in active_tasks:
            del active_tasks[task_id]

async def handle_submit(request: web.Request) -> web.Response:
    """Handle video URL submission."""
    try:
        data = await request.json()
        url = data.get('url')
        if not url:
            return web.json_response({
                "error": "No URL provided"
            }, status=400)
            
        # Generate task ID
        task_id = f"task_{len(active_tasks)}"
        
        # Start processing
        asyncio.create_task(process_video(url, task_id))
        
        return web.json_response({
            "task_id": task_id,
            "status": "started",
            "message": "Processing started"
        })
        
    except Exception as e:
        return web.json_response({
            "error": str(e)
        }, status=500)

async def handle_status(request: web.Request) -> web.Response:
    """Get status of a processing task."""
    task_id = request.match_info.get('task_id')
    if not task_id or task_id not in active_tasks:
        return web.json_response({
            "error": "Task not found"
        }, status=404)
        
    return web.json_response(active_tasks[task_id])

async def handle_list_tasks(request: web.Request) -> web.Response:
    """List all active tasks."""
    return web.json_response({
        "tasks": active_tasks
    })

async def init_app() -> web.Application:
    """Initialize the web application."""
    app = web.Application()
    app.router.add_post('/submit', handle_submit)
    app.router.add_get('/status/{task_id}', handle_status)
    app.router.add_get('/tasks', handle_list_tasks)
    return app

def main():
    """Run the server."""
    app = asyncio.run(init_app())
    web.run_app(app, host='localhost', port=8080)

if __name__ == "__main__":
    main() 