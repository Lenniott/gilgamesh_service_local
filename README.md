# Gilgamesh Media Processing Service

A FastAPI-based service that processes social media content (Instagram posts, reels, and YouTube videos) to extract media, text, and transcripts. The service provides a unified API for downloading, processing, and analyzing content from various platforms.

## Features

- **Multi-Platform Support**
  - Instagram posts and reels
  - YouTube videos and shorts
  - Extracts media, text, and metadata

- **Content Processing**
  - Video scene detection and extraction
  - OCR text extraction from images and video frames
  - Audio transcription for videos
  - Tag and metadata extraction

- **Performance & Resource Management**
  - URL-based caching with configurable TTL
  - Background task processing
  - Temporary file management
  - Configurable base64 encoding for videos

## Prerequisites

- Python 3.11+
- FFmpeg (for video processing)
- Tesseract (for OCR)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd gilgamesh_service_local
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install system dependencies:
```bash
# macOS
brew install ffmpeg tesseract

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install ffmpeg tesseract-ocr
```

## Usage

### Starting the Service

```bash
python -m app.main
```

The service will start on `http://localhost:8500` with automatic API documentation available at `http://localhost:8500/docs`.

### API Endpoints

#### 1. Process Content
```bash
POST /process
```

Process one or more URLs to extract content.

**Request Body:**
```json
{
    "urls": [
        "https://www.instagram.com/p/...",
        "https://youtube.com/shorts/..."
    ],
    "encode_base64": true,    // Optional: Include base64-encoded video data
    "cleanup_temp": true      // Optional: Clean up temp files and cache after processing
}
```

**Response:**
```json
{
    "status": "success",
    "results": [
        {
            "url": "https://www.instagram.com/p/...",
            "title": "Post Title",
            "description": "Post description...",
            "tags": ["tag1", "tag2"],
            "videos": [  // For video content
                {
                    "id": "uuid",
                    "scenes": [
                        {
                            "start": 0.0,
                            "end": 5.0,
                            "text": "OCR text from frame",
                            "confidence": 1.0,
                            "video": "base64-encoded video segment"  // If encode_base64=true
                        }
                    ],
                    "transcript": [
                        {
                            "start": 0.0,
                            "end": 5.0,
                            "text": "Transcribed text"
                        }
                    ]
                }
            ],
            "images": [  // For image content
                {
                    "text": "OCR text from image"
                }
            ]
        }
    ]
}
```

#### 2. Cache Management

**Get Cache Statistics:**
```bash
GET /cache/stats
```

**Response:**
```json
{
    "total_entries": 10,
    "total_size_bytes": 1024000,
    "oldest_entry": "2024-03-20T10:00:00",
    "newest_entry": "2024-03-20T15:00:00",
    "ttl_hours": 24
}
```

**Clear Cache:**
```bash
POST /cleanup?clear_cache=true
```

#### 3. Cleanup

**Clean Temporary Files and Cache:**
```bash
POST /cleanup
```

**Options:**
- `clear_cache=true` (default): Clear both temp files and cache
- `clear_cache=false`: Clear only temp files

### Examples

1. Process an Instagram post:
```bash
curl -X POST "http://localhost:8500/process" \
     -H "Content-Type: application/json" \
     -d '{"urls": ["https://www.instagram.com/p/..."]}' \
     | python -m json.tool
```

2. Process multiple URLs without base64 encoding:
```bash
curl -X POST "http://localhost:8500/process" \
     -H "Content-Type: application/json" \
     -d '{
         "urls": [
             "https://www.instagram.com/p/...",
             "https://youtube.com/shorts/..."
         ],
         "encode_base64": false
     }' \
     | python -m json.tool
```

3. Process without cleanup:
```bash
curl -X POST "http://localhost:8500/process" \
     -H "Content-Type: application/json" \
     -d '{
         "urls": ["https://www.instagram.com/p/..."],
         "cleanup_temp": false
     }' \
     | python -m json.tool
```

## Configuration

The service uses the following default configurations:

- **Cache:**
  - TTL: 24 hours
  - Location: `app/cache/`
  - Thread-safe operations

- **Temporary Files:**
  - Location: `app/temp/`
  - UUID-based directories
  - Automatic cleanup (configurable)

- **Video Processing:**
  - Scene detection threshold: 0.22
  - Target video width: 480px
  - Base64 encoding: enabled by default

## Error Handling

The service provides detailed error responses:

```json
{
    "status": "error",
    "error": "Error message",
    "url": "https://..."  // For URL-specific errors
}
```

Common error scenarios:
- Invalid URLs
- Unsupported content types
- Processing failures
- Cache/storage issues

## Development

### Project Structure
```
gilgamesh_service_local/
├── app/
│   ├── main.py           # FastAPI application
│   ├── media_utils.py    # Core processing logic
│   ├── cache.py         # Caching implementation
│   ├── downloaders.py   # Media downloaders
│   ├── ocr_utils.py     # OCR processing
│   ├── transcription.py # Audio transcription
│   └── utils.py         # Helper functions
├── requirements.txt
└── README.md
```

### Adding New Features

1. Follow the existing code structure
2. Add type hints and docstrings
3. Update the plan.md with new tasks
4. Add appropriate error handling
5. Update this README with new features

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Add your license information here] 