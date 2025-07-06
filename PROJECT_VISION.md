# Gilgamesh Media Processing Service - Project Vision Document

## 1. PROJECT OVERVIEW

### 1.1 Mission Statement
The Gilgamesh Media Processing Service is a **unified API platform** for processing social media video content with AI-powered analysis, transcription, and semantic search capabilities. The system transforms raw video URLs into structured, searchable content with detailed metadata and contextual understanding.

### 1.2 Core Principles
- **Single Responsibility**: Each function has one clear purpose
- **Carousel-First Design**: Native support for multi-video content
- **AI-Agnostic**: Support multiple AI providers without vendor lock-in
- **Credit Optimization**: Intelligent caching to minimize AI API costs
- **Semantic Search**: Individual vector points for granular content discovery
- **Data Integrity**: Robust error handling and data validation

### 1.3 Success Metrics
- **Processing Speed**: < 30 seconds per video
- **AI Cost Efficiency**: > 80% cache hit rate for repeat URLs
- **Search Accuracy**: Semantic search with timestamp precision
- **System Reliability**: 99.9% uptime, graceful error handling
- **API Simplicity**: Single endpoint with clear parameters

## 2. SYSTEM ARCHITECTURE

### 2.1 Core Components

#### **Input Layer**
- **URL Validation**: Instagram, YouTube, TikTok URL support
- **Carousel Detection**: Automatic multi-video identification
- **Media Download**: Robust download with retry logic

#### **Processing Layer**
- **Audio Transcription**: Whisper-based speech-to-text
- **Scene Analysis**: AI-powered visual content description
- **Content Tagging**: Automatic tag extraction and categorization
- **Duplicate Detection**: URL-based caching for AI credit savings

#### **Storage Layer**
- **PostgreSQL**: Structured metadata, transcripts, scene descriptions
- **Qdrant**: Vector embeddings for semantic search
- **File System**: Temporary video files (auto-cleanup)

#### **API Layer**
- **Single Endpoint**: `/process` with full parameter control
- **Retrieval APIs**: Search, list, and individual video access
- **Vectorization**: Bulk processing of existing content

### 2.2 Data Flow
```
URL Input → Validation → Download → Processing → Storage → API Response
    ↓           ↓          ↓          ↓         ↓        ↓
  Carousel   Media      Audio      Scene    Vector   Structured
 Detection  Download  Transcribe  Analysis  Search   Response
```

## 3. API SPECIFICATION

### 3.1 Core Processing Endpoint

#### **POST /process**
**Purpose**: Main video processing with full parameter control
**Input**: ProcessRequest
**Output**: Unified processing response

**Parameters:**
```json
{
  "url": "https://www.instagram.com/p/...",
  "save_video": true,        // Save video file to database
  "transcribe": true,        // Generate transcript
  "describe": true,          // Generate scene descriptions
  "save_to_postgres": true,  // Save to PostgreSQL
  "save_to_qdrant": true,    // Save to vector database
  "include_base64": false    // Include video base64 in response
}
```

**Response Structure:**
```json
{
  "success": true,
  "message": "Processing completed successfully",
  "url": "original_url",
  "normalized_url": "cleaned_url",
  "carousel_info": {
    "is_carousel": false,
    "total_videos": 1,
    "processed_videos": 1
  },
  "processing": {
    "download": true,
    "total_videos_processed": 1,
    "ai_credits_saved_count": 0,
    "database_operations": {
      "postgres_enabled": true,
      "qdrant_enabled": true,
      "postgres_saves": 1,
      "qdrant_saves": 1
    }
  },
  "videos": [
    {
      "carousel_index": 0,
      "video_id": "uuid-here",
      "processing": {
        "transcription": true,
        "scene_analysis": true,
        "used_existing_data": false,
        "ai_credits_saved": false
      },
      "results": {
        "transcript_data": [...],
        "scenes_data": [...],
        "tags": [...]
      },
      "database": {
        "postgres_saved": true,
        "qdrant_saved": true,
        "video_stored": true
      }
    }
  ],
  "video_ids": ["uuid-here"]
}
```

### 3.2 Retrieval Endpoints

#### **GET /video/{video_id}**
**Purpose**: Retrieve specific video by ID
**Parameters**: `video_id`, `include_base64`
**Output**: Single video data

#### **GET /carousel**
**Purpose**: Retrieve all videos from carousel URL
**Parameters**: `url`, `include_base64`
**Output**: All videos from carousel

#### **GET /search**
**Purpose**: Semantic search across all content
**Parameters**: `q` (query), `limit`
**Output**: Ranked search results with timestamps

#### **GET /videos**
**Purpose**: List recent videos
**Parameters**: `limit`
**Output**: Recent videos with metadata

### 3.3 Vectorization Endpoint

#### **POST /vectorize/existing**
**Purpose**: Bulk vectorization of existing database content
**Parameters**: `limit`, `dry_run`, `verbose`
**Output**: Vectorization progress and results

## 4. DATA MODELS

### 4.1 Video Record (PostgreSQL)
```sql
CREATE TABLE simple_videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT NOT NULL,
    normalized_url TEXT NOT NULL,
    carousel_index INTEGER DEFAULT 0,
    video_base64 TEXT,
    has_video BOOLEAN DEFAULT FALSE,
    transcript JSONB,
    descriptions JSONB,
    tags TEXT[],
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    vectorized_at TIMESTAMP,
    vector_id TEXT,
    embedding_model TEXT DEFAULT 'text-embedding-3-small'
);
```

### 4.2 Vector Records (Qdrant)

#### **Transcript Segment Vector**
```json
{
  "vector_id": "uuid-4",
  "collection": "video_transcript_segments",
  "embedding": [0.123, -0.456, ...],
  "metadata": {
    "video_id": "uuid-4",
    "segment_index": 2,
    "text": "Hello everyone, welcome to my cooking show",
    "start": 5.2,
    "end": 8.7,
    "duration": 3.5,
    "url": "https://www.instagram.com/p/...",
    "carousel_index": 0,
    "type": "transcript_segment"
  }
}
```

#### **Scene Description Vector**
```json
{
  "vector_id": "uuid-4",
  "collection": "video_scene_descriptions",
  "embedding": [0.234, -0.567, ...],
  "metadata": {
    "video_id": "uuid-4",
    "scene_index": 1,
    "description": "A person in a modern kitchen chopping vegetables",
    "start_time": 10.0,
    "end_time": 15.5,
    "duration": 5.5,
    "url": "https://www.instagram.com/p/...",
    "carousel_index": 0,
    "type": "scene_description",
    "tags": ["kitchen", "cooking", "vegetables"]
  }
}
```

## 5. CORE FUNCTIONS

### 5.1 Processing Functions

#### **process_video_unified_simple()**
**Purpose**: Main processing function with all options
**Input**: URL + processing parameters
**Output**: Unified response structure
**Responsibilities**:
- URL validation and normalization
- Carousel detection and handling
- Duplicate detection (AI credit savings)
- Audio transcription
- Scene analysis
- Database storage (PostgreSQL + Qdrant)
- Response formatting

#### **download_media_and_metadata()**
**Purpose**: Download video files and extract metadata
**Input**: URL
**Output**: Downloaded files + metadata
**Responsibilities**:
- Multi-platform support (Instagram, YouTube, TikTok)
- Carousel detection
- Metadata extraction
- Temporary file management

#### **transcribe_audio()**
**Purpose**: Convert audio to timestamped transcript
**Input**: Video file path
**Output**: Timestamped transcript segments
**Responsibilities**:
- Audio extraction from video
- Whisper-based transcription
- Timestamp synchronization
- Error handling for silent videos

#### **extract_scenes_with_ai_analysis()**
**Purpose**: Generate AI-powered scene descriptions
**Input**: Video file + optional transcript context
**Output**: Scene descriptions with timestamps
**Responsibilities**:
- Frame extraction at key intervals
- AI-powered visual analysis
- Transcript context integration
- Tag extraction

### 5.2 Database Functions

#### **SimpleVideoDatabase**
**Purpose**: Unified database operations
**Responsibilities**:
- PostgreSQL connection management
- Qdrant client management
- Video CRUD operations
- Vectorization status tracking
- Connection cleanup

#### **save_video_carousel()**
**Purpose**: Save video with carousel support
**Input**: Video data + carousel index
**Output**: Video ID
**Responsibilities**:
- Carousel-aware storage
- Metadata preservation
- Duplicate prevention

#### **update_vectorization_status()**
**Purpose**: Track vectorization progress
**Input**: Video ID + vector count
**Output**: Success status
**Responsibilities**:
- Vectorization timestamp
- Vector count tracking
- Model version tracking

### 5.3 Search Functions

#### **search_videos_simple()**
**Purpose**: Semantic search across all content
**Input**: Query string + limit
**Output**: Ranked results with timestamps
**Responsibilities**:
- Query embedding generation
- Multi-collection search
- Result ranking and deduplication
- Timestamp-based filtering

## 6. AI PROVIDERS

### 6.1 Current Support
- **OpenAI**: GPT-4 Vision, Whisper, text-embedding-3-small
- **Gemini**: Vision analysis (secondary)

### 6.2 Provider Selection Logic
```python
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")
if AI_PROVIDER == "openai":
    # Use OpenAI for all operations
elif AI_PROVIDER == "gemini":
    # Use Gemini for vision, OpenAI for embeddings
```

### 6.3 Future Extensibility
- **Anthropic Claude**: Vision analysis
- **Local Models**: Whisper local, CLIP embeddings
- **Hybrid Approaches**: Best model per task

## 7. SYSTEM BOUNDARIES

### 7.1 What We DO
- ✅ **Process social media videos** (Instagram, YouTube, TikTok)
- ✅ **Generate transcripts** with timestamps
- ✅ **Analyze visual content** with AI
- ✅ **Create searchable vectors** for semantic search
- ✅ **Handle carousels** with multiple videos
- ✅ **Optimize AI costs** through intelligent caching
- ✅ **Provide unified API** for all operations

### 7.2 What We DON'T DO
- ❌ **Live streaming** or real-time processing
- ❌ **Video editing** or manipulation
- ❌ **Content moderation** or filtering
- ❌ **User authentication** or authorization
- ❌ **Content hosting** or CDN services
- ❌ **Social media posting** or interaction
- ❌ **Payment processing** or billing
- ❌ **Analytics dashboards** or reporting UI

### 7.3 External Dependencies
- **Required**: PostgreSQL, Qdrant, OpenAI API
- **Optional**: Gemini API (secondary provider)
- **System**: FFmpeg, yt-dlp, gallery-dl

## 8. ERROR HANDLING

### 8.1 Error Categories
- **Input Errors**: Invalid URLs, unsupported formats
- **Processing Errors**: Download failures, AI API errors
- **Storage Errors**: Database connection issues
- **System Errors**: Resource exhaustion, timeouts

### 8.2 Error Response Format
```json
{
  "success": false,
  "error": "Human-readable error message",
  "error_code": "DOWNLOAD_FAILED",
  "details": {
    "url": "problematic_url",
    "reason": "Network timeout"
  }
}
```

### 8.3 Graceful Degradation
- **Audio failures**: Continue with visual analysis
- **AI failures**: Return partial results
- **Database failures**: Return processing results without storage
- **Network issues**: Implement retry logic with exponential backoff

## 9. PERFORMANCE REQUIREMENTS

### 9.1 Processing Targets
- **Single video**: < 30 seconds end-to-end
- **Carousel (5 videos)**: < 2 minutes total
- **Concurrent requests**: 10 simultaneous
- **Memory usage**: < 2GB per request

### 9.2 Storage Targets
- **PostgreSQL**: < 100ms query response
- **Qdrant**: < 200ms vector search
- **File cleanup**: Automatic temp file removal
- **Vector storage**: < 1MB per video

### 9.3 Cost Optimization
- **AI credits**: 80%+ cache hit rate
- **Storage**: Efficient vector compression
- **Compute**: Parallel processing where possible
- **Network**: Minimal data transfer

## 10. FUTURE ROADMAP

### 10.1 Near-term (Next 3 months)
- **Enhanced error handling** with specific error codes
- **Batch processing** for multiple URLs
- **Performance monitoring** and metrics
- **API rate limiting** and throttling

### 10.2 Medium-term (Next 6 months)
- **Additional platforms** (Twitter, LinkedIn)
- **Advanced search filters** (date, duration, tags)
- **Webhook notifications** for async processing
- **API versioning** and backward compatibility

### 10.3 Long-term (Next 12 months)
- **Machine learning pipeline** for content classification
- **Real-time processing** for live content
- **Multi-language support** for global content
- **Advanced analytics** and insights

## 11. DEVELOPMENT GUIDELINES

### 11.1 Code Standards
- **Function naming**: Clear, descriptive names
- **Error handling**: Explicit try-catch blocks
- **Logging**: Structured logging with context
- **Documentation**: Inline comments for complex logic

### 11.2 Testing Requirements
- **Unit tests**: All core functions
- **Integration tests**: Database operations
- **End-to-end tests**: Full processing pipeline
- **Performance tests**: Load and stress testing

### 11.3 Deployment Standards
- **Environment variables**: All configuration externalized
- **Docker containers**: Consistent deployment
- **Health checks**: Comprehensive monitoring
- **Rollback procedures**: Safe deployment practices

---

## CONCLUSION

This vision document serves as the definitive guide for the Gilgamesh Media Processing Service. All development decisions should align with these principles and boundaries. Any proposed changes that deviate from this vision must be explicitly discussed and approved before implementation.

**Remember**: Our goal is to be the **best** at processing social media videos with AI, not to be everything to everyone. Stay focused, stay simple, stay effective. 