# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import uvicorn
import os

# Import your actual functions
from app.media_utils import process_url
from app.cleanup import cleanup_temp_folder
from app.stitch_scenes import stitch_scenes

app = FastAPI()

class DownloadRequest(BaseModel):
    urls: List[str]

class StitchRequest(BaseModel):
    json_path: str

@app.post("/process")
def download_handler(request: DownloadRequest):
    try:
        results = []
        for url in request.urls:
            result = process_url(url)
            results.append(result)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cleanup")
def cleanup_handler():
    try:
        cleanup_temp_folder()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stitch")
def stitch_handler(request: StitchRequest):
    try:
        output_path = os.path.join(os.path.dirname(request.json_path), "stitched.mp4")
        stitch_scenes(request.json_path, list(range(10)), output_path)  # Example: stitch first 10 scenes
        return {"status": "success", "output_path": output_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8500)
