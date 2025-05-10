from fastapi import FastAPI, Request
from downloader import download_media


app = FastAPI()

@app.post("/process")
async def process(request: Request):
    data = await request.json()
    url = data.get("url")

    if not url:
        return {"status": "error", "message": "Missing URL"}

    try:
        result = download_media(url)
        return {
            "status": "ok",
            "source": result["source"],
            "tags": result["tags"],
            "media_type": result.get("media_type", "unknown"),
            "media_count": result.get("media_count", 1),
            "transcription": result.get("transcription", ""),
            "transcriptions": result.get("transcriptions", [])
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
