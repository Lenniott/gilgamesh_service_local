# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os

# Import your actual functions
from app.media_utils import process_url, process_and_cleanup
from app.cleanup import cleanup_temp_folder
from app.stitch_scenes import stitch_scenes_to_base64
from app.downloaders import download_media_and_metadata
from app.video_processing import cleanup_temp_files

app = FastAPI()

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

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8500)
