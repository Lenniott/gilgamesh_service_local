# Gilgamesh Media Processing Service

A FastAPI-based service that processes social media content (Instagram posts, reels, and YouTube videos) with AI-powered scene analysis and transcript integration. **Now supports Instagram carousels with multiple videos!** The service provides a unified API for downloading, processing, and analyzing content with smart AI credit management.

## Features

- **Multi-Platform Support**
  - Instagram posts and reels **with carousel support**
  - YouTube videos and shorts
  - TikTok videos

- **Instagram Carousel Processing**
  - **Automatic multi-video detection** from carousel URLs
  - **Individual processing** of each video in carousel
  - **Unified storage** with carousel indexing
  - **Smart credit management** per video

- **AI-Powered Content Processing**
  - **Dual AI Support**: Choose between OpenAI GPT-4 Vision or Google Gemini 2.0 Flash
  - Enhanced prompts with step-by-step instructions, benefits, and safety considerations
  - Audio transcription with timestamping
  - Smart AI credit management (avoids duplicate processing)
  - Enhanced video context for better scene descriptions

- **Database Integration**
  - PostgreSQL for structured data storage
  - Single-table architecture with carousel support
  - Automatic video base64 storage per carousel video
  - JSON storage for transcripts and scene descriptions

- **Performance & Resource Management**
  - Smart caching to avoid AI credit waste
  - Automatic temporary file cleanup
  - Graceful audio handling (videos without audio)
  - Concurrent request management

## Prerequisites

- Python 3.11+
- FFmpeg (for video processing)
- PostgreSQL database
- **AI Provider**: Choose one or both:
  - OpenAI API key (for GPT-4 Vision)
  - Google Gemini API key (for Gemini 2.0 Flash)

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
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install ffmpeg
```

5. Set up environment variables:
```bash
# Create .env file
cp .env.example .env

# Configure your credentials
POSTGRES_URL=postgresql://user:password@localhost:5432/database

# AI Provider Configuration (choose one or both)
AI_PROVIDER=openai  # or "gemini" for Google Gemini
OPENAI_API_KEY=your_openai_api_key      # for OpenAI GPT-4 Vision
GEMINI_API_KEY=your_gemini_api_key      # for Google Gemini 2.0 Flash
```

6. Set up the database:
```bash
python setup_simple_db.py
```

## AI Provider Configuration

### Choose Your AI Provider

The service supports two AI providers for scene analysis:

#### **OpenAI GPT-4 Vision (Default)**
```bash
AI_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
```
- **Best for**: Common exercise names, broader context understanding
- **Output style**: "The exercise being performed is a dynamic stretch known as the World's Greatest Stretch"
- **Tags**: General fitness terminology

#### **Google Gemini 2.0 Flash Experimental**
```bash
AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
```
- **Best for**: Technical terminology, detailed biomechanical descriptions
- **Output style**: "Dynamic hip flexor stretch with thoracic rotation, sometimes referred to as an open book lunge"
- **Tags**: Technical movement patterns and muscle groups
- **Advantage**: Typically more cost-effective than GPT-4 Vision

### Enhanced Prompts

Both providers use enhanced prompts that include:
- **Detailed descriptions** with step-by-step instructions
- **Exercise benefits** and practical applications
- **Prerequisites** and safety considerations
- **Comprehensive tags** covering exercise type, muscle groups, and movement patterns

### Smart Provider Selection
- **Automatic fallback**: Falls back to OpenAI if Gemini library not installed
- **Same API**: No changes to existing endpoints - just set environment variable
- **Credit management**: Existing data reuse works with both providers

## Core Use Cases

### 1. Full Processing (Complete Video Analysis)
**Use Case:** Process a video with all features - save video, generate transcript, create AI scene descriptions, store in database.

**Single Video:**
```bash
curl -X POST "http://localhost:8500/process/full" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.instagram.com/p/YOUR_POST_ID/"}'
```

**Instagram Carousel (Multiple Videos):**
```bash
curl -X POST "http://localhost:8500/process/full" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.instagram.com/p/DLPa9I7sU9Y/"}'
```

**Carousel Response:**
```json
{
  "success": true,
  "message": "Carousel processing completed successfully",
  "carousel_info": {
    "is_carousel": true,
    "total_videos": 3,
    "processed_videos": 3
  },
  "videos": [
    {
      "carousel_index": 0,
      "video_id": "uuid-1",
      "processing": {"transcription": true, "scene_analysis": true},
      "results": {"transcript_data": [...], "scenes_data": [...]}
    },
    {
      "carousel_index": 1,
      "video_id": "uuid-2",
      "processing": {"transcription": true, "scene_analysis": true},
      "results": {"transcript_data": [...], "scenes_data": [...]}
    },
    {
      "carousel_index": 2,
      "video_id": "uuid-3",
      "processing": {"transcription": true, "scene_analysis": true},
      "results": {"transcript_data": [...], "scenes_data": [...]}
    }
  ],
  "video_ids": ["uuid-1", "uuid-2", "uuid-3"]
}
```

**Perfect for:** Content archival, complete video analysis, building video libraries, **carousel content processing**.

### 2. Raw Transcript Only (No Storage)
**Use Case:** Extract transcript data without any database storage or scene analysis.

```bash
curl -X POST "http://localhost:8500/process/transcript-only" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.instagram.com/p/DLPa9I7sU9Y/"}'
```

**Carousel Transcript Response:**
```json
{
  "success": true,
  "url": "https://www.instagram.com/p/DLPa9I7sU9Y/",
  "carousel_info": {
    "is_carousel": true,
    "total_videos": 3
  },
  "transcript_data": [
    {
      "carousel_index": 0,
      "transcript": [
        {"start": 0.0, "end": 5.2, "text": "Welcome to today's workout session..."}
      ]
    },
    {
      "carousel_index": 1,
      "transcript": [
        {"start": 0.0, "end": 8.1, "text": "Now let's move to the next exercise..."}
      ]
    },
    {
      "carousel_index": 2,
      "transcript": [
        {"start": 0.0, "end": 6.3, "text": "Finally, we'll cool down with stretches..."}
      ]
    }
  ]
}
```

**Perfect for:** Quick transcript extraction, content analysis, subtitle generation, **multi-video transcript compilation**.

### 3. Vector Database Storage (Qdrant)
**Use Case:** Process transcript and store in vector database for semantic search with **individual vector points** for precise, timestamp-based search.

```bash
curl -X POST "http://localhost:8500/process/qdrant-only" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.instagram.com/p/YOUR_POST_ID/"}'
```

**Revolutionary Approach:** Each transcript segment and scene description becomes its own vector point for granular search.

**Perfect for:** Building searchable knowledge bases, semantic content discovery, **timestamp-precise search**, **carousel content indexing**.

## Instagram Carousel Support

### How Carousels Work

**URL Processing:**
- Input: `https://www.instagram.com/p/DLPa9I7sU9Y` (carousel with 3 videos)
- System automatically detects multiple videos
- Each video processed individually with `carousel_index` (0, 1, 2, etc.)
- All videos stored under same normalized URL

**Database Storage:**
```sql
-- Each video gets its own row with carousel_index
simple_videos:
  url='https://www.instagram.com/p/DLPa9I7sU9Y', carousel_index=0, video_base64='...', transcript=[...], descriptions=[...]
  url='https://www.instagram.com/p/DLPa9I7sU9Y', carousel_index=1, video_base64='...', transcript=[...], descriptions=[...]
  url='https://www.instagram.com/p/DLPa9I7sU9Y', carousel_index=2, video_base64='...', transcript=[...], descriptions=[...]
```

### Carousel-Specific Endpoints

#### `/process/carousel` - Get Existing Carousel Videos
```bash
curl -X POST "http://localhost:8500/process/carousel" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.instagram.com/p/DLPa9I7sU9Y/", "include_base64": false}'
```

#### `/carousel` - Get Carousel by URL (Query Parameter)
```bash
curl "http://localhost:8500/carousel?url=https://www.instagram.com/p/DLPa9I7sU9Y/"
```

### Smart Carousel Processing

**Credit Management:**
- Each video in carousel checked individually
- Only missing videos/features processed
- Existing videos returned from database
- Significant AI credit savings on repeat requests

**Example - Mixed Processing:**
```json
{
  "videos": [
    {
      "carousel_index": 0,
      "processing": {"ai_credits_saved": true},  // Already processed
      "message": "Retrieved from database"
    },
    {
      "carousel_index": 1,
      "processing": {"ai_credits_saved": false}, // Newly processed
      "message": "Processed with AI analysis"
    },
    {
      "carousel_index": 2,
      "processing": {"ai_credits_saved": true},  // Already processed
      "message": "Retrieved from database"
    }
  ]
}
```

## API Endpoints

### 🚨 Quick Reference - Recommended Endpoints

**For most use cases, use these endpoints:**

| Endpoint | Use Case | Request Body |
|----------|----------|--------------|
| `/process/simple` | **Flexible processing** | `{"url": "...", "save_video": true, "transcribe": true, "describe": true, "save_to_postgres": true, "save_to_qdrant": true}` |
| `/process/full` | **Complete processing** | `{"url": "..."}` |
| `/process/transcript-only` | **Transcript only** | `{"url": "..."}` |

**⚠️ Common Error:** Don't use `/process/unified` unless you understand the legacy string parameters!

### Core Processing Endpoints

#### `/process/full` - Complete Processing
```bash
POST /process/full
```

**Request Body:**
```json
{
    "url": "https://www.instagram.com/p/..."
}
```

- **Function:** Download, save, transcribe, describe, save to PostgreSQL
- **Parameters:** Just URL - everything else is automatic
- **Use Case:** Full video processing with all features
- **Carousel Support:** ✅ Processes all videos in carousel

#### `/process/transcript-only` - Raw Transcript Only
```bash
POST /process/transcript-only
```

**Request Body:**
```json
{
    "url": "https://www.instagram.com/p/..."
}
```

- **Function:** Download, transcribe, return raw transcript without saving
- **Parameters:** Just URL
- **Response:** Clean transcript array only (per carousel video)
- **Use Case:** Quick transcript extraction
- **Carousel Support:** ✅ Returns transcripts for all videos

#### `/process/qdrant-only` - Vector Storage (Coming Soon)
```bash
POST /process/qdrant-only
```

**Request Body:**
```json
{
    "url": "https://www.instagram.com/p/..."
}
```

- **Function:** Download, transcribe, save to Qdrant without saving video
- **Parameters:** Just URL
- **Use Case:** Vector database storage for semantic search
- **Carousel Support:** ✅ Processes all videos for vector storage
- **Status:** ⚠️ Not yet implemented in simple processor

### Flexible Processing Endpoints

#### `/process/simple` - Configurable Processing
```bash
POST /process/simple
```

**Request Body:**
```json
{
    "url": "https://www.instagram.com/p/...",
    "save_video": true,         // Save video base64 to database
    "transcribe": true,         // Generate transcript
    "describe": true,           // Generate AI scene descriptions
    "save_to_postgres": true,   // Save to PostgreSQL database
    "save_to_qdrant": true,     // Save to Qdrant vector database (requires OpenAI)
    "include_base64": false     // Include base64 in response (large!)
}
```

**Database Control:** ✅ Independent control over PostgreSQL and Qdrant storage
**Carousel Support:** ✅ All options apply to each video in carousel
**Embedding:** Uses OpenAI for consistent vector embeddings

#### `/process/unified` - Legacy Advanced Processing ⚠️
```bash
POST /process/unified
```

**Request Body:**
```json
{
    "url": "https://www.instagram.com/p/...",
    "save": false,           // Save video to database
    "transcribe": "raw",     // ⚠️ STRING: "raw", "timestamp", or null (NOT boolean!)
    "describe": false,       // Generate scene descriptions
    "save_to_postgres": true,// Save to PostgreSQL database
    "save_to_qdrant": true   // Save to Qdrant vector database
}
```

**⚠️ IMPORTANT - Transcribe Parameter:**
- **Type:** `string | null` (NOT boolean!)
- `"raw"` - Enable raw transcription
- `"timestamp"` - Enable timestamped transcription  
- `null` - Disable transcription
- **Common Error:** Sending `true/false` will cause 422 validation error

**Carousel Support:** ✅ Full compatibility with carousel processing
**Use Case:** Legacy endpoint for backward compatibility
**Status:** ⚠️ **Legacy Endpoint** - Use `/process/simple` for new integrations
**Note:** Currently maps to full processor with PostgreSQL and Qdrant support

### Carousel-Specific Endpoints

#### `/process/carousel` - Get Carousel Videos
```bash
POST /process/carousel
```

**Request Body:**
```json
{
    "url": "https://www.instagram.com/p/...",
    "include_base64": false
}
```

#### `/carousel` - Get Carousel by URL
```bash
GET /carousel?url=https://www.instagram.com/p/...&include_base64=false
```

### Utility Endpoints

#### `/video/{video_id}` - Get Specific Video
```bash
GET /video/{video_id}?include_base64=false
```

#### `/search` - Search Videos
```bash
GET /search?q=exercise&limit=10
```

#### `/videos` - List Recent Videos
```bash
GET /videos?limit=20
```

#### `/health` - Health Check
```bash
GET /health
```

## Smart AI Credit Management

The system automatically checks for existing data to avoid wasting AI credits:

**First Request (Carousel):**
```json
{
  "success": true,
  "message": "Carousel processing completed successfully",
  "processing": {
    "total_videos_processed": 3,
    "ai_credits_saved_count": 0
  },
  "videos": [
    {"carousel_index": 0, "processing": {"ai_credits_saved": false}},
    {"carousel_index": 1, "processing": {"ai_credits_saved": false}},
    {"carousel_index": 2, "processing": {"ai_credits_saved": false}}
  ]
}
```

**Second Request (Same Carousel URL):**
```json
{
  "success": true,
  "message": "Carousel processing completed successfully",
  "processing": {
    "total_videos_processed": 3,
    "ai_credits_saved_count": 3
  },
  "videos": [
    {"carousel_index": 0, "processing": {"ai_credits_saved": true}},
    {"carousel_index": 1, "processing": {"ai_credits_saved": true}},
    {"carousel_index": 2, "processing": {"ai_credits_saved": true}}
  ]
}
```

## 🚨 Common API Errors & Solutions

### 422 Validation Error: "Input should be a valid string"

**Problem:** You're sending boolean values to `/process/unified` endpoint
```json
{
  "url": "https://www.instagram.com/p/...",
  "transcribe": true  // ❌ WRONG - This causes 422 error
}
```

**Solutions:**

1. **Use `/process/simple` instead (Recommended):**
```json
{
  "url": "https://www.instagram.com/p/...",
  "transcribe": true  // ✅ CORRECT - Boolean values work here
}
```

2. **Fix the `/process/unified` request:**
```json
{
  "url": "https://www.instagram.com/p/...",
  "transcribe": "raw"  // ✅ CORRECT - String value required
}
```

### Parameter Type Reference

| Endpoint | `transcribe` Type | `describe` Type | `save_video` Type | `save_to_postgres` Type | `save_to_qdrant` Type |
|----------|------------------|-----------------|------------------|------------------------|---------------------|
| `/process/simple` | `boolean` | `boolean` | `boolean` | `boolean` | `boolean` |
| `/process/full` | N/A (auto) | N/A (auto) | N/A (auto) | N/A (auto) | N/A (auto) |
| `/process/unified` | `string \| null` | `boolean` | `boolean` | `boolean` | `boolean` |

## Enhanced AI Scene Analysis

The system provides contextual scene analysis:

1. **Transcript Integration:** AI uses spoken content to enhance visual scene descriptions
2. **Video Context:** When available, AI uses full video context for better scene understanding
3. **Graceful Audio Handling:** Videos without audio are processed with visual analysis only
4. **Carousel Context:** Each video in carousel analyzed individually with its own context

**Example Scene Analysis (Carousel Video):**
```json
{
  "carousel_index": 1,
  "scenes": [
    {
      "start_time": 0.0,
      "end_time": 8.5,
      "ai_description": "Person demonstrating proper squat form with emphasis on knee alignment, as mentioned in the transcript about 'keeping knees behind toes'",
      "ai_tags": ["squat", "form", "knee-alignment", "exercise-technique"],
      "has_transcript": true,
      "has_video_context": true
    }
  ]
}
```

## Database Schema

The system uses a simplified single-table approach with carousel support:

```sql
simple_videos (
    id UUID PRIMARY KEY,
    url TEXT NOT NULL,               -- Normalized URL (without img_index)
    carousel_index INTEGER DEFAULT 0, -- Index for carousel videos (0 for single videos)
    video_base64 TEXT,               -- Base64 encoded video
    transcript JSONB,                -- Transcript segments
    descriptions JSONB,              -- AI scene descriptions
    tags TEXT[],                     -- Extracted tags
    metadata JSONB,                  -- Additional metadata
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    
    -- Unique constraint for URL + carousel_index combination
    UNIQUE(url, carousel_index)
)
```

**Carousel Storage Example:**
```sql
-- Single video (carousel_index = 0)
INSERT INTO simple_videos (url, carousel_index, video_base64, ...)
VALUES ('https://www.instagram.com/p/ABC123/', 0, 'base64_data', ...);

-- Carousel videos (carousel_index = 0, 1, 2)
INSERT INTO simple_videos (url, carousel_index, video_base64, ...)
VALUES 
  ('https://www.instagram.com/p/DLPa9I7sU9Y/', 0, 'base64_video_1', ...),
  ('https://www.instagram.com/p/DLPa9I7sU9Y/', 1, 'base64_video_2', ...),
  ('https://www.instagram.com/p/DLPa9I7sU9Y/', 2, 'base64_video_3', ...);
```

## Examples

### Complete Carousel Processing
```bash
# Full processing: save + transcribe + describe + database storage
curl -X POST "http://localhost:8500/process/full" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.instagram.com/p/DLPa9I7sU9Y/"}'
```

### Flexible Processing Options
```bash
# Custom processing with specific options
curl -X POST "http://localhost:8500/process/simple" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://www.instagram.com/p/DLPa9I7sU9Y/",
       "save_video": true,
       "transcribe": true,
       "describe": true,
       "include_base64": false
     }'
```

### Quick Carousel Transcript Extraction
```bash
# Transcript only - no database storage
curl -X POST "http://localhost:8500/process/transcript-only" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.instagram.com/p/DLPa9I7sU9Y/"}' \
     | jq '.transcript_data'
```

### Retrieve Existing Carousel Data
```bash
# Get stored carousel videos with AI analysis
curl -X POST "http://localhost:8500/process/carousel" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.instagram.com/p/DLPa9I7sU9Y/"}'

# Alternative GET method
curl "http://localhost:8500/carousel?url=https://www.instagram.com/p/DLPa9I7sU9Y/"
```

### Advanced Database Control
```bash
# PostgreSQL only (skip Qdrant)
curl -X POST "http://localhost:8500/process/unified" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://www.instagram.com/p/DLPa9I7sU9Y/",
       "save": true,
       "transcribe": "raw",
       "describe": true,
       "save_to_postgres": true,
       "save_to_qdrant": false
     }'

# Future: Both databases (when Qdrant is implemented)
curl -X POST "http://localhost:8500/process/unified" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://www.instagram.com/p/DLPa9I7sU9Y/",
       "save": true,
       "transcribe": "raw", 
       "describe": true,
       "save_to_postgres": true,
       "save_to_qdrant": true
     }'
```

### Search and Discovery
```bash
# Search for specific exercises
curl "http://localhost:8500/search?q=squat&limit=5"

# List recent videos
curl "http://localhost:8500/videos?limit=10"

# Get specific video by ID
curl "http://localhost:8500/video/your-video-id-here"
```

## Response Format

### Carousel Processing Response
```json
{
  "success": true,
  "message": "Carousel processing completed successfully",
  "url": "https://www.instagram.com/p/DLPa9I7sU9Y/",
  "normalized_url": "https://www.instagram.com/p/DLPa9I7sU9Y",
  "carousel_info": {
    "is_carousel": true,
    "total_videos": 7,
    "processed_videos": 7
  },
  "processing": {
    "download": true,
    "total_videos_processed": 7,
    "ai_credits_saved_count": 0
  },
  "videos": [
    {
      "carousel_index": 0,
      "video_id": "uuid-here",
      "processing": {
        "transcription": false,
        "scene_analysis": true,
        "used_existing_data": false,
        "ai_credits_saved": false
      },
      "results": {
        "transcript_data": null,
        "scenes_data": [
          {
            "start_time": 0.0,
            "end_time": 21.53,
            "description": "Person performing bodyweight squats with proper form...",
            "analysis_success": true
          }
        ],
        "tags": ["balance", "bodyweight", "strength", "lower body", "squat"]
      },
      "database": {
        "saved": true,
        "video_stored": true
      }
    }
    // ... more videos
  ],
  "video_ids": ["uuid-1", "uuid-2", "uuid-3", ...]
}
```

### Search Response
```json
{
  "success": true,
  "query": "squat",
  "results": [
    {
      "id": "uuid-here",
      "url": "https://www.instagram.com/p/DLPa9I7sU9Y",
      "carousel_index": 0,
      "tags": ["balance", "bodyweight", "strength", "lower body", "squat"],
      "first_description": "Person performing bodyweight squats...",
      "created_at": "2025-07-04T20:13:17.225341+00:00"
    }
  ],
  "count": 1
}
```

### Get Existing Carousel Videos
```bash
curl "http://localhost:8500/carousel?url=https://www.instagram.com/p/DLPa9I7sU9Y/"
```

### Custom Carousel Processing Options
```bash
curl -X POST "http://localhost:8500/process/simple" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://www.instagram.com/p/DLPa9I7sU9Y/",
       "save_video": true,
       "transcribe": true,
       "describe": false,
       "include_base64": false
     }'
```

## 🔍 Vector Search Structure

### Individual Vector Points for Precise Search

The system creates **individual vector points** for each transcript segment and scene description, enabling granular, timestamp-based search.

#### Two Collections:
- **`video_transcript_segments`** - Each transcript segment as individual vector
- **`video_scene_descriptions`** - Each scene description as individual vector

#### Transcript Segment Vector Example:
```json
{
  "vector_id": "uuid-4",
  "collection": "video_transcript_segments",
  "embedding": [0.123, -0.456, ...],
  "metadata": {
    "video_id": "d63023c6-9062-4b2b-b9b1-78e489da0a4d",
    "segment_index": 2,
    "text": "Hello everyone, welcome to my cooking show",
    "start": 5.2,
    "end": 8.7,
    "duration": 3.5,
    "url": "https://www.instagram.com/p/...",
    "carousel_index": 0,
    "type": "transcript_segment",
    "tags": [],
    "created_at": "2024-12-23T...",
    "vectorized_at": "2024-12-23T..."
  }
}
```

#### Scene Description Vector Example:
```json
{
  "vector_id": "uuid-4",
  "collection": "video_scene_descriptions", 
  "embedding": [0.234, -0.567, ...],
  "metadata": {
    "video_id": "d63023c6-9062-4b2b-b9b1-78e489da0a4d",
    "scene_index": 1,
    "description": "A person in a modern kitchen chopping vegetables",
    "start_time": 10.0,
    "end_time": 15.5,
    "duration": 5.5,
    "frame_count": 165,
    "url": "https://www.instagram.com/p/...",
    "carousel_index": 0,
    "type": "scene_description",
    "tags": ["kitchen", "cooking", "vegetables"],
    "created_at": "2024-12-23T...",
    "vectorized_at": "2024-12-23T..."
  }
}
```

#### Benefits:
- **Precise Search**: Find exact moments in videos, not just entire videos
- **Timestamp Accuracy**: Each vector contains exact timing information
- **Granular Retrieval**: Return specific segments instead of entire transcripts
- **Better Relevance**: Semantic search matches specific content, not mixed content
- **Scalable**: Each video can have dozens of searchable segments

#### Vectorization Options:

**HTTP Endpoint (Recommended):**
```bash
# Vectorize existing videos via API
curl -X POST "http://localhost:8500/vectorize/existing" \
     -H "Content-Type: application/json" \
     -d '{"limit": 5, "dry_run": true}'

# Examples:
curl -X POST "http://localhost:8500/vectorize/existing" \
     -H "Content-Type: application/json" \
     -d '{"dry_run": true}'                                 # See what would be processed

curl -X POST "http://localhost:8500/vectorize/existing" \
     -H "Content-Type: application/json" \
     -d '{"limit": 10}'                                     # Process 10 videos

curl -X POST "http://localhost:8500/vectorize/existing" \
     -H "Content-Type: application/json" \
     -d '{}'                                                # Process all unvectorized videos
```

**Command Line (Alternative):**
```bash
# Vectorize existing videos that haven't been vectorized yet
python vectorize_existing_videos.py [--limit N] [--dry-run] [--verbose]

# Examples:
python vectorize_existing_videos.py --dry-run --limit 5    # See what would be processed
python vectorize_existing_videos.py --limit 10             # Process 10 videos
python vectorize_existing_videos.py                        # Process all unvectorized videos
```

## Error Handling

The service provides detailed error responses:

```json
{
    "success": false,
    "error": "No video files found after download",
    "url": "https://..."
}
```

Common scenarios:
- Invalid URLs
- Videos without audio (handled gracefully)
- Processing failures
- Database connection issues
- **Carousel processing failures (individual video failures don't stop others)**

## Configuration

### Environment Variables
```bash
# Required
OPENAI_API_KEY=your_openai_api_key
POSTGRES_URL=postgresql://user:password@localhost:5432/database

# Optional
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT_SECONDS=30
```

### Default Settings
- **Concurrent Requests:** 10 maximum
- **Request Timeout:** 30 seconds
- **Scene Detection Threshold:** 0.22
- **Video Downscaling:** 480px width
- **Automatic Cleanup:** Enabled
- **Carousel Support:** Enabled by default

## Development

### Project Structure
```
gilgamesh_service_local/
├── app/
│   ├── main.py                      # FastAPI application with carousel endpoints
│   ├── simple_unified_processor.py  # Core processing logic with carousel support
│   ├── simple_db_operations.py     # Database operations with carousel methods
│   ├── ai_scene_analysis.py        # GPT-4 Vision analysis
│   ├── scene_detection.py          # Scene detection
│   ├── transcription.py            # Audio transcription
│   ├── downloaders.py              # Media downloaders (carousel-aware)
│   └── db_connections.py           # Database connections
├── setup_simple_db.py              # Database setup
├── create_simple_videos_table.sql  # Database schema with carousel support
├── requirements.txt
└── README.md
```

### Testing
```bash
# Run the simplified system test
python test_simple_system.py

# Run database tests
python test_db_direct.py

# Test carousel functionality
curl -X POST "http://localhost:8500/process/full" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.instagram.com/p/DLPa9I7sU9Y/"}'
```

## Performance

- **Smart Caching:** Avoids duplicate AI processing per carousel video
- **Automatic Cleanup:** Temporary files cleaned after processing
- **Concurrent Processing:** Handles multiple requests efficiently
- **Optimized Database:** Single-table design for fast queries
- **Carousel Efficiency:** Individual video credit management in carousels

## Contributing

1. Fork the repository
2. Create a feature branch
3. Follow the existing code patterns
4. Add tests for new features
5. Update documentation
6. Create a Pull Request

## License

[Add your license information here] 