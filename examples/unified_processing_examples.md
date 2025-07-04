# Unified Processing System Examples

This document provides comprehensive examples of how to use the new unified processing system with PostgreSQL and Qdrant integration.

## 🚀 Quick Start

### 1. Just Get Transcript (No Saving)
```bash
curl -X POST "http://localhost:8500/process/unified" \
     -H "Content-Type: application/json" \
     -d '{
         "url": "https://www.youtube.com/shorts/2hvRmabCWS4",
         "transcribe": "timestamp",
         "save_to_postgres": false,
         "save_to_qdrant": false
     }'
```

**Response:**
```json
{
  "status": "success",
  "result": {
    "url": "https://www.youtube.com/shorts/2hvRmabCWS4",
    "processing_options": {
      "save": false,
      "transcribe": "timestamp",
      "describe": false,
      "save_to_postgres": false,
      "save_to_qdrant": false
    },
    "results": {
      "transcript": [
        {
          "start": 0.0,
          "end": 5.2,
          "text": "This is a mobility exercise demonstration..."
        }
      ],
      "processing_complete": true
    },
    "errors": []
  }
}
```

### 2. AI Scene Analysis Only (No Saving)
```bash
curl -X POST "http://localhost:8500/process/unified" \
     -H "Content-Type: application/json" \
     -d '{
         "url": "https://www.youtube.com/shorts/2hvRmabCWS4",
         "describe": true,
         "save_to_postgres": false,
         "save_to_qdrant": false
     }'
```

**Response:**
```json
{
  "status": "success",
  "result": {
    "results": {
      "scenes": [
        {
          "start_time": 0.0,
          "end_time": 3.3,
          "ai_description": "Person demonstrating a forward fold mobility exercise, moving from standing position to deep forward bend",
          "ai_tags": ["forward-fold", "hamstring-stretch", "mobility", "flexibility", "spine-flexion"],
          "analysis_success": true
        }
      ]
    }
  }
}
```

## 🗄️ Database Storage Examples

### 3. Save to Qdrant Only (For Semantic Search)
```bash
curl -X POST "http://localhost:8500/process/unified" \
     -H "Content-Type: application/json" \
     -d '{
         "url": "https://www.youtube.com/shorts/2hvRmabCWS4",
         "transcribe": "timestamp",
         "describe": true,
         "save_to_postgres": false,
         "save_to_qdrant": true
     }'
```

**Response:**
```json
{
  "status": "success",
  "result": {
    "results": {
      "transcription": {
        "postgresql_saved": false,
        "qdrant_saved": true,
        "chunks_created": 3,
        "vector_ids": ["uuid1", "uuid2", "uuid3"]
      },
      "scene_analysis": {
        "postgresql_saved": false,
        "qdrant_saved": true,
        "scenes_processed": 5,
        "vector_ids": ["uuid4", "uuid5", "uuid6", "uuid7", "uuid8"]
      }
    }
  }
}
```

### 4. Save Video Base64 to PostgreSQL
```bash
curl -X POST "http://localhost:8500/process/unified" \
     -H "Content-Type: application/json" \
     -d '{
         "url": "https://www.youtube.com/shorts/2hvRmabCWS4",
         "save": true,
         "save_to_postgres": true,
         "save_to_qdrant": false
     }'
```

**Response:**
```json
{
  "status": "success",
  "result": {
    "results": {
      "video_saved": true,
      "video_id": "550e8400-e29b-41d4-a716-446655440000",
      "processing_complete": true
    }
  }
}
```

## 🚀 Complete Pipeline Examples

### 5. Full Processing (Everything Enabled)
```bash
curl -X POST "http://localhost:8500/process/unified" \
     -H "Content-Type: application/json" \
     -d '{
         "url": "https://www.youtube.com/shorts/2hvRmabCWS4",
         "save": true,
         "transcribe": "timestamp",
         "describe": true,
         "save_to_postgres": true,
         "save_to_qdrant": true
     }'
```

**Response:**
```json
{
  "status": "success",
  "result": {
    "url": "https://www.youtube.com/shorts/2hvRmabCWS4",
    "processing_options": {
      "save": true,
      "transcribe": "timestamp", 
      "describe": true,
      "save_to_postgres": true,
      "save_to_qdrant": true
    },
    "results": {
      "video_saved": true,
      "video_id": "550e8400-e29b-41d4-a716-446655440000",
      "transcription": {
        "postgresql_saved": true,
        "qdrant_saved": true,
        "chunks_created": 3,
        "vector_ids": ["uuid1", "uuid2", "uuid3"]
      },
      "scene_analysis": {
        "postgresql_saved": true,
        "qdrant_saved": true,
        "scenes_processed": 5,
        "vector_ids": ["uuid4", "uuid5", "uuid6", "uuid7", "uuid8"]
      },
      "processing_complete": true
    },
    "errors": []
  }
}
```

### 6. Knowledge Base Mode (Transcripts + AI Analysis to Qdrant)
```bash
curl -X POST "http://localhost:8500/process/unified" \
     -H "Content-Type: application/json" \
     -d '{
         "url": "https://www.youtube.com/shorts/2hvRmabCWS4",
         "transcribe": "raw",
         "describe": true,
         "save_to_postgres": false,
         "save_to_qdrant": true
     }'
```

## 📊 Processing Options Explained

| Option | Values | Description |
|--------|--------|-------------|
| `save` | `true`/`false` | Save complete video as base64 in PostgreSQL |
| `transcribe` | `null`, `"raw"`, `"timestamp"` | Transcription mode |
| `describe` | `true`/`false` | AI scene analysis with GPT-4 Vision |
| `save_to_postgres` | `true`/`false` | Save to PostgreSQL database |
| `save_to_qdrant` | `true`/`false` | Save to Qdrant vector database |

### Transcription Modes:
- **`null`**: No transcription
- **`"raw"`**: Single text block (full transcript)
- **`"timestamp"`**: Time-chunked segments (30-second windows)

## 🔍 Use Case Scenarios

### Scenario 1: Content Archive
**Goal**: Store videos for long-term archival with full metadata
```json
{
  "save": true,
  "transcribe": "timestamp",
  "describe": true,
  "save_to_postgres": true,
  "save_to_qdrant": false
}
```

### Scenario 2: Semantic Search System
**Goal**: Enable vector search across video content
```json
{
  "save": false,
  "transcribe": "timestamp",
  "describe": true,
  "save_to_postgres": false,
  "save_to_qdrant": true
}
```

### Scenario 3: RAG System Integration
**Goal**: Store content for LLM retrieval systems
```json
{
  "save": false,
  "transcribe": "raw",
  "describe": true,
  "save_to_postgres": false,
  "save_to_qdrant": true
}
```

### Scenario 4: Quick Processing
**Goal**: Get transcript/analysis without storage
```json
{
  "save": false,
  "transcribe": "raw",
  "describe": true,
  "save_to_postgres": false,
  "save_to_qdrant": false
}
```

### Scenario 5: Complete Solution
**Goal**: Full processing with all storage options
```json
{
  "save": true,
  "transcribe": "timestamp",
  "describe": true,
  "save_to_postgres": true,
  "save_to_qdrant": true
}
```

## 🗄️ Database Schema Used

### PostgreSQL Tables:
1. **`gilgamesh_sm_posts`** - Main post/video metadata
2. **`gilgamesh_sm_videos`** - Video records (with optional base64)
3. **`gilgamesh_sm_video_scenes`** - Scene/transcript chunks
4. **`gilgamesh_sm_scene_exercise_metadata`** - AI analysis metadata

### Qdrant Collections:
1. **`gilgamesh_transcripts`** - Transcript embeddings
2. **`gilgamesh_scenes`** - Scene description embeddings

## 🔧 Environment Setup

Required `.env` variables:
```env
# PostgreSQL
PG_DBNAME=your_database
PG_USER=your_username
PG_PASSWORD=your_password
PG_HOST=localhost
PG_PORT=5432

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_qdrant_key

# OpenAI
OPENAI_API_KEY=sk-your-openai-key
```

## 🧪 Testing the System

Run the comprehensive test:
```bash
python test_unified_system.py
```

This will test:
- ✅ Database connections
- ✅ Transcription only
- ✅ AI analysis only  
- ✅ Qdrant storage
- ✅ PostgreSQL storage
- ✅ Full pipeline
- ✅ Vector retrieval

## 🎯 Key Benefits

1. **Flexibility**: Choose exactly what you want to save and where
2. **Performance**: Only run the processing you need
3. **Scalability**: Separate storage systems for different use cases
4. **Retrieval**: Get full video context from any search result
5. **Integration**: Easy to integrate with existing RAG/LLM systems 