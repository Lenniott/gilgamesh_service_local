# CHANGELOG

## [2.0.0] - 2024-12-XX - Complete Database Integration + Unified Processing System

### 🚀 **MAJOR NEW FEATURES**
- **PostgreSQL Integration**: Full database storage for videos, transcripts, and AI scene analysis
- **Qdrant Vector Database**: Semantic search and retrieval of video content through embeddings
- **OpenAI Embeddings**: Automatic vectorization of transcripts and scene descriptions
- **Unified Processing API**: `/process/unified` endpoint with flexible save/transcribe/describe options
- **Flexible Storage Options**: Choose PostgreSQL and/or Qdrant storage independently
- **Video Base64 Storage**: Save complete videos as base64 in PostgreSQL for archival
- **Intelligent Chunking**: Time-based transcript chunking (30-second segments) with metadata
- **Full Video Retrieval**: Get complete video information from any vector search result

### 🗄️ **DATABASE ARCHITECTURE**
- **Multi-table Structure**: Uses `gilgamesh_sm_posts`, `gilgamesh_sm_videos`, `gilgamesh_sm_video_scenes`, `gilgamesh_sm_scene_exercise_metadata`
- **Vector Linking**: Each database record includes `vector_id` for Qdrant integration
- **Rich Metadata**: Comprehensive metadata storage for retrieval and analytics
- **Automatic Collections**: Creates Qdrant collections `gilgamesh_transcripts` and `gilgamesh_scenes`
- **Connection Pooling**: AsyncPG connection pooling for high performance
- **Transaction Safety**: All database operations wrapped in transactions

### 📡 **NEW API CAPABILITIES**

#### Unified Processing Endpoint: `/process/unified`
```json
{
  "url": "https://youtube.com/shorts/example",
  "save": true,
  "transcribe": "timestamp", 
  "describe": true,
  "save_to_postgres": true,
  "save_to_qdrant": true
}
```

#### Processing Options:
- **`save`**: Store video as base64 in PostgreSQL
- **`transcribe`**: `"raw"` (single block) or `"timestamp"` (chunked segments)
- **`describe`**: AI scene analysis with GPT-4 Vision
- **`save_to_postgres`**: Save to PostgreSQL database
- **`save_to_qdrant`**: Save to Qdrant vector database

### 🔍 **RETRIEVAL CAPABILITIES**
- **Semantic Search**: Find videos by transcript or scene content
- **Full Context Recovery**: Any vector hit provides complete original video metadata
- **Cross-Collection Search**: Search both transcripts and scene descriptions
- **Rich Payload Data**: Each vector includes timestamps, URLs, and full context

### 🛠️ **TECHNICAL IMPLEMENTATION**
- **New Modules**:
  - `app/db_connections.py` - Unified database connection management
  - `app/db_operations.py` - Database operations with flexible storage
  - `app/unified_processor.py` - Complete processing pipeline
- **Dependencies Added**: `asyncpg`, `psycopg2-binary`, `qdrant-client`
- **Environment Variables**: PostgreSQL, Qdrant, and OpenAI configuration via `.env`
- **Graceful Degradation**: Works without database connections (returns data only)
- **Automatic Cleanup**: Temporary files cleaned after processing

### 📋 **USE CASES ENABLED**

1. **Knowledge Base**: Store video content for semantic search
2. **Archival**: Full video base64 storage in PostgreSQL
3. **AI Analysis**: Scene-by-scene understanding with GPT-4 Vision
4. **Flexible Workflows**: Mix and match storage options per use case
5. **RAG Systems**: Vector search for video content in LLM applications

## [1.2.0] - 2024-12-XX - Enhanced Scene Detection + AI Analysis

### ADDED
- **Enhanced Scene Detection**: Finds extreme movement positions (start, valley, peak, end) within video scenes
- **GPT-4 Vision Integration**: AI analysis of extreme frames to generate scene descriptions and tags
- **Automatic Frame Cleanup**: Deletes all frame images after AI analysis
- **Complete Scene Analysis Pipeline**: `extract_scenes_with_ai_analysis()` function
- **AI Scene Analysis Module**: `app/ai_scene_analysis.py` for GPT-4 Vision processing
- **OpenCV Frame Analysis**: Visual difference calculation to find extreme positions
- **Structured JSON Output**: Clean scene data with AI descriptions and tags

### TECHNICAL FEATURES
- **Movement Analysis**: Detects press-up extremes, mobility exercise ranges, and key positions
- **Concurrent AI Processing**: Up to 3 parallel GPT-4 Vision API calls
- **Graceful Degradation**: Works without OpenAI API key (skips AI analysis)
- **Smart Frame Extraction**: 3 FPS sampling with visual difference scoring
- **Automatic Cleanup**: All temporary frame images deleted after processing
- **Environment Loading**: Added `python-dotenv` for `.env` file support
- **Updated AI Model**: Using `gpt-4o` (current model) instead of deprecated `gpt-4-vision-preview`

### NEW RESPONSE STRUCTURE
```json
{
  "scenes": [
    {
      "start_time": 4.33,
      "end_time": 7.67,
      "ai_description": "Person performing downward movement in mobility exercise",
      "ai_tags": ["mobility", "exercise", "movement", "stretching", "flexibility"],
      "analysis_success": true
    }
  ]
}
```

## [1.1.0] - 2024-12-XX - OCR Removal Update

### REMOVED
- **Complete OCR functionality** - Removed all optical character recognition features
- **Dependencies**: `easyocr`, `pytesseract`, `pillow`, `Pillow==10.1.0`
- **System dependencies**: `tesseract-ocr` from Dockerfile
- **Files**: Deleted `app/ocr_utils.py` (60 lines of OCR code)
- **Functions**: Removed `resize_image_if_needed()` from `app/utils.py`
- **Database fields**: Removed `onscreen_text` from video scenes, `descriptive_text` from images
- **JSON response fields**: Removed `text` fields from scenes and images

### CHANGED
- **Faster processing** - No OCR overhead during video/image processing
- **Smaller Docker image** - Removed Tesseract system dependency
- **Simplified database schema** - Cleaner structure without OCR text fields
- **Updated API responses** - Images now return `filename` instead of `text`
- **Updated SQL queries** - All database insert queries cleaned of OCR references
- **Updated documentation** - README, curl_commands.md reflect OCR-free workflow

### TECHNICAL DETAILS
- Scene detection now returns timestamps and confidence only
- Image processing returns filename instead of extracted text
- All test mocks updated to remove OCR dependencies
- N8N workflows need updating to remove OCR text processing

### BENEFITS
- 🚀 **Performance**: Faster media processing without OCR bottleneck
- 📦 **Size**: Reduced Docker image size (no Tesseract)
- 🔧 **Maintenance**: Fewer dependencies to manage
- 💾 **Database**: Simpler schema without text fields
- 🧹 **Code**: Cleaner codebase with 60+ fewer lines

### FIXED
- **Cleanup endpoint bug**: Fixed `/cleanup` endpoint that was missing required `temp_dir` parameter
- **Cache clearing**: `/cleanup?clear_cache_data=true` now works properly

### MIGRATION NOTES
- Existing database columns `onscreen_text` and `descriptive_text` will be empty
- N8N workflows referencing OCR text fields need updating
- JSON response structure changed - `text` fields no longer present 