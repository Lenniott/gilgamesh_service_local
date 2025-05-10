from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import os
import json
from typing import List, Optional
import uuid
from pathlib import Path

from media_utils import media_utils
from stitch_scenes import stitch_scenes
from cleanup import cleanup_temp_folder

app = FastAPI(title="Media Processing Service")

@app.post("/process")
async def process_media_endpoint(files: List[UploadFile] = File(...)):
    """
    Process uploaded media files to detect scenes and create scene files.
    """
    try:
        # Create a unique session ID
        session_id = str(uuid.uuid4())
        temp_dir = os.path.join("app", "temp", session_id)
        os.makedirs(temp_dir, exist_ok=True)
        
        # Save uploaded files
        saved_files = []
        for file in files:
            file_path = os.path.join(temp_dir, file.filename)
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            saved_files.append(file_path)
        
        # Process the media
        result = media_utils(saved_files, temp_dir)
        
        return JSONResponse({
            "session_id": session_id,
            "result": result
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stitch/{session_id}")
async def stitch_scenes_endpoint(
    session_id: str,
    scene_indices: List[int],
    output_filename: str = "output.mp4"
):
    """
    Stitch together specific scenes from a processed session.
    """
    try:
        result_json = os.path.join("app", "temp", session_id, "result.json")
        if not os.path.exists(result_json):
            raise HTTPException(status_code=404, detail="Session not found")
        
        output_path = os.path.join("app", "temp", session_id, output_filename)
        stitch_scenes(result_json, scene_indices, output_path)
        
        return JSONResponse({
            "message": "Scenes stitched successfully",
            "output_path": output_path
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cleanup")
async def cleanup_endpoint():
    """
    Clean up all temporary files.
    """
    try:
        cleanup_temp_folder()
        return JSONResponse({"message": "Cleanup completed successfully"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8500) 