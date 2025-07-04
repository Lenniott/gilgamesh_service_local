# Gilgamesh Service - All CURL Commands

## 1. PROCESS SINGLE URL (Main Endpoint)

### Basic Processing
```bash
curl -X POST "http://localhost:8500/process" \
     -H "Content-Type: application/json" \
     -d '{
         "url": "https://www.youtube.com/shorts/2hvRmabCWS4"
     }'
```

### With All Parameters
```bash
curl -X POST "http://localhost:8500/process" \
     -H "Content-Type: application/json" \
     -d '{
         "url": "https://www.instagram.com/p/...",
         "cleanup_temp": true,
         "threshold": 0.22,
         "encode_base64": true
     }'
```

### Fast Processing (No Base64)
```bash
curl -X POST "http://localhost:8500/process" \
     -H "Content-Type: application/json" \
     -d '{
         "url": "https://www.youtube.com/shorts/2hvRmabCWS4",
         "encode_base64": false,
         "cleanup_temp": false,
         "threshold": 0.22
     }'
```

## 2. BATCH PROCESSING

### Process Multiple URLs
```bash
curl -X POST "http://localhost:8500/process/batch" \
     -H "Content-Type: application/json" \
     -d '{
         "urls": [
             "https://www.instagram.com/p/...",
             "https://www.youtube.com/shorts/...",
             "https://www.tiktok.com/@user/video/..."
         ],
         "cleanup_temp": true,
         "threshold": 0.22
     }'
```

## 3. DOWNLOAD ONLY (No Processing)

### Basic Download
```bash
curl -X POST "http://localhost:8500/download" \
     -H "Content-Type: application/json" \
     -d '{
         "url": "https://www.youtube.com/shorts/2hvRmabCWS4"
     }'
```

## 4. CLEANUP OPERATIONS

### Clean Temp Files Only
```bash
curl -X POST "http://localhost:8500/cleanup" \
     -H "Content-Type: application/json"
```

### Clean Temp Files + Cache
```bash
curl -X POST "http://localhost:8500/cleanup?clear_cache_data=true" \
     -H "Content-Type: application/json"
```

## 5. CACHE MANAGEMENT

### Get Cache Stats
```bash
curl -X GET "http://localhost:8500/cache/stats" \
     -H "Content-Type: application/json"
```

## 6. STITCH SCENES

### Combine Video Scenes
```bash
curl -X POST "http://localhost:8500/stitch" \
     -H "Content-Type: application/json" \
     -d '{
         "scenes": [
             {
                 "video": "base64-encoded-video-1",
                 "audio": "base64-encoded-audio-1"
             },
             {
                 "video": "base64-encoded-video-2"
             }
         ]
     }'
```

## PARAMETERS EXPLAINED

### URLRequest Parameters:
- **url** (required): The social media URL to process
- **cleanup_temp** (optional, default: true): Delete temp files after processing
- **threshold** (optional, default: 0.22): Scene detection sensitivity (0.1-1.0)
- **encode_base64** (optional, default: true): Include base64 video data in response

### URLBatchRequest Parameters:
- **urls** (required): Array of URLs to process
- **cleanup_temp** (optional, default: true): Delete temp files after processing  
- **threshold** (optional, default: 0.22): Scene detection sensitivity

### Response Structure:
```json
{
    "status": "success",
    "result": {
        "url": "https://...",
        "title": "Post Title",
        "description": "Post description",
        "tags": ["tag1", "tag2"],
        "videos": [{
            "id": "video_id",
            "scenes": [{
                "start": 0.0,
                "end": 5.0,
                "confidence": 1.0,
                "video": "base64-data"
            }],
            "transcript": [{
                "start": 0.0,
                "end": 5.0,
                "text": "Transcribed text"
            }]
        }],
        "images": [{
            "filename": "image.jpg"
        }],
        "temp_dir": "/path/to/temp"
    }
}
```

## TEST URLS

### YouTube Shorts
```bash
curl -X POST "http://localhost:8500/process" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.youtube.com/shorts/2hvRmabCWS4"}'
```

### Instagram Post
```bash
curl -X POST "http://localhost:8500/process" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.instagram.com/p/[POST_ID]/"}'
```

### Instagram Reel
```bash
curl -X POST "http://localhost:8500/process" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.instagram.com/reel/[REEL_ID]/"}'
```

## ERROR HANDLING

### Check Service Status
```bash
curl -X GET "http://localhost:8500/docs"
```

### Test Connection
```bash
curl -X GET "http://localhost:8500"
``` 