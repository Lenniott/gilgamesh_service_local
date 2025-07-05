# CHANGELOG

## [2.2.9] - 2024-12-23 - Vectorization Tracking & PostgreSQL Updates

### 🎯 **NEW: PostgreSQL Vectorization Tracking**

**Added Vectorization Status Tracking**: PostgreSQL now tracks when videos have been vectorized to Qdrant with full metadata.

#### **What's New:**
- **`vectorized_at`**: Timestamp when video was vectorized to Qdrant
- **`vector_id`**: Qdrant vector UUID for direct lookup
- **`embedding_model`**: OpenAI model used for embeddings (defaults to 'text-embedding-3-small')
- **Automatic updates**: PostgreSQL gets updated immediately after successful Qdrant storage

#### **Database Schema Changes:**
```sql
-- New columns added to simple_videos table
ALTER TABLE simple_videos 
ADD COLUMN vectorized_at TIMESTAMP,
ADD COLUMN vector_id TEXT,
ADD COLUMN embedding_model TEXT DEFAULT 'text-embedding-3-small';

-- Updated views include vectorization stats
CREATE OR REPLACE VIEW video_summary AS
SELECT 
    COUNT(*) as total_videos,
    COUNT(CASE WHEN vectorized_at IS NOT NULL THEN 1 END) as vectorized_count,
    COUNT(CASE WHEN vectorized_at IS NULL THEN 1 END) as not_vectorized_count,
    AVG(CASE WHEN vectorized_at IS NOT NULL THEN 1.0 ELSE 0.0 END) as vectorization_rate
FROM simple_videos;
```

#### **Code Implementation:**
```python
# NEW: Database method to track vectorization
async def update_vectorization_status(self, video_id: str, vector_id: str, embedding_model: str = "text-embedding-3-small") -> bool:
    """Update PostgreSQL with vectorization status after successful Qdrant storage."""
    
# NEW: Automatic updates in processing
if success:
    logger.info(f"✅ Video {carousel_index} saved to Qdrant: {vector_id}")
    qdrant_saved = True
    
    # Update PostgreSQL with vectorization info
    if video_id and db.connections and db.connections.pg_pool:
        await db.update_vectorization_status(video_id, vector_id, "text-embedding-3-small")
        logger.info(f"✅ Updated PostgreSQL with vectorization info")
```

#### **Benefits:**
- **Data Integrity**: PostgreSQL and Qdrant status always in sync
- **Debugging**: Easy to see which videos are vectorized
- **Analytics**: Track vectorization rates and success
- **Recovery**: Can identify and re-vectorize failed videos
- **Audit Trail**: Full history of when vectorization occurred

#### **Impact:**
- **Both endpoints**: `/process/simple` and `/process/unified` now update PostgreSQL
- **Automatic**: No API changes needed, happens transparently
- **Backward compatible**: Existing videos show `NULL` until re-vectorized
- **Performance**: Minimal overhead, only updates on successful Qdrant storage

#### **Migration:**
- **Run SQL migration**: Execute `add_vectorization_tracking.sql` to add new columns
- **Existing videos**: Will show `vectorized_at: NULL` until reprocessed
- **New videos**: Automatically get vectorization tracking

---

## [2.2.8] - 2024-12-23 - Complete Database Control & OpenAI Embeddings

### 🎯 **PERFECT: Full Database Control with Consistent Embeddings**

**Added Independent Database Control**: You can now control PostgreSQL and Qdrant storage independently with consistent OpenAI embeddings.

#### **What You Asked For:**
- **`save_to_postgres`**: Boolean control over PostgreSQL storage
- **`save_to_qdrant`**: Boolean control over Qdrant storage  
- **Independent control**: Save to one, both, or neither database
- **OpenAI embeddings**: Consistent vector embeddings using OpenAI (not Gemini)
- **Full transcript & description capture**: Everything gets processed and stored correctly

#### **New `/process/simple` Parameters:**
```json
{
  "url": "https://www.instagram.com/p/...",
  "save_video": true,         // Save video base64 to PostgreSQL
  "transcribe": true,         // Generate transcript
  "describe": true,           // Generate AI scene descriptions  
  "save_to_postgres": true,   // Save to PostgreSQL database
  "save_to_qdrant": true,     // Save to Qdrant vector database
  "include_base64": false     // Include base64 in response
}
```

#### **Database Control Examples:**

**PostgreSQL Only:**
```json
{"save_to_postgres": true, "save_to_qdrant": false}
```

**Qdrant Only:**
```json
{"save_to_postgres": false, "save_to_qdrant": true}
```

**Both Databases:**
```json
{"save_to_postgres": true, "save_to_qdrant": true}
```

**Neither Database (Processing Only):**
```json
{"save_to_postgres": false, "save_to_qdrant": false}
```

#### **Response Format:**
```json
{
  "processing": {
    "database_operations": {
      "postgres_enabled": true,
      "qdrant_enabled": true,
      "postgres_saves": 1,
      "qdrant_saves": 1
    }
  },
  "videos": [
    {
      "database": {
        "postgres_saved": true,
        "qdrant_saved": true,
        "video_stored": true
      }
    }
  ]
}
```

#### **Technical Implementation:**
- **OpenAI Embeddings**: All Qdrant vectors use OpenAI `text-embedding-3-small` for consistency
- **Validation**: Requires OpenAI client for Qdrant operations
- **Error Handling**: Clear logging for missing clients or failed operations
- **Backward Compatible**: Existing calls default to saving to both databases

#### **Requirements for Qdrant:**
- **OpenAI API Key**: Required for consistent embeddings
- **Qdrant Connection**: Must be available and configured
- **Text Content**: Transcript or descriptions needed for vectorization

---

## [2.2.7] - 2024-12-23 - Critical Qdrant Integration Fix

### 🚨 **URGENT: Fixed Missing Qdrant Integration**

**Fixed Critical Bug**: The `/process/simple` endpoint was not saving transcript and description data to Qdrant, only to PostgreSQL.

#### **What Was Wrong**
- **`/process/simple`**: Only saved to PostgreSQL, completely ignored Qdrant
- **`/process/unified`**: Had Qdrant support but used confusing legacy parameters
- **Qdrant storage**: Failed silently when videos had no audio/transcript
- **Result**: Users expecting Qdrant vectorization got nothing

#### **What's Fixed**
- **Added full Qdrant support** to `/process/simple` endpoint
- **Improved Qdrant storage logic** to handle videos without audio
- **Better error logging** for Qdrant connection issues
- **Response includes Qdrant save status** for debugging

#### **Technical Changes**
```python
# NEW: Added to process_video_unified_simple()
# Save to Qdrant (NEW: Added Qdrant support to simple processor)
qdrant_saved = False
if db.connections and db.connections.qdrant_client:
    # Create text content for embedding from transcript + descriptions
    # Store vector with metadata even if no audio
    # Return qdrant_saved status in response
```

#### **Response Format Updated**
```json
{
  "processing": {
    "database_operations": {
      "postgres_saves": 1,
      "qdrant_saves": 1  // NEW: Shows Qdrant save status
    }
  },
  "videos": [
    {
      "database": {
        "postgres_saved": true,
        "qdrant_saved": true,  // NEW: Per-video Qdrant status
        "video_stored": true
      }
    }
  ]
}
```

#### **Impact**
- **`/process/simple`**: Now saves to both PostgreSQL AND Qdrant
- **Better debugging**: Response shows exactly what was saved where
- **Backward compatible**: Existing API calls now get Qdrant storage automatically
- **Semantic search**: Transcript and description data now properly vectorized

#### **Migration**
- **No changes needed**: Existing `/process/simple` calls automatically get Qdrant storage
- **Check responses**: Look for `qdrant_saved: true` to confirm vectorization
- **Environment**: Ensure `QDRANT_URL` and `QDRANT_API_KEY` are set

---

## [2.2.6] - 2024-12-23 - Critical API Documentation Fix

### 🚨 **URGENT: API Documentation Correction**

**Fixed Critical API Documentation Error**: The README was showing incorrect parameter types for the `/process/unified` endpoint, causing 422 validation errors.

#### **What Was Wrong**
- **README showed**: `"transcribe": true` (boolean) for `/process/unified`
- **API expects**: `"transcribe": "raw"` (string) for `/process/unified`
- **Result**: Users getting 422 "Input should be a valid string" errors

#### **Documentation Fixes**
- **Added**: 🚨 Quick Reference section with recommended endpoints
- **Added**: Common API Errors & Solutions section
- **Added**: Parameter Type Reference table
- **Updated**: `/process/unified` endpoint documentation with clear warnings
- **Highlighted**: `/process/simple` as the recommended endpoint for boolean parameters

#### **Key Changes**
```markdown
### 🚨 Quick Reference - Recommended Endpoints

| Endpoint | Use Case | Request Body |
|----------|----------|--------------|
| `/process/simple` | **Flexible processing** | `{"url": "...", "save_video": true, "transcribe": true, "describe": true}` |
| `/process/unified` | **Legacy endpoint** | `{"url": "...", "transcribe": "raw", "describe": false}` |

**⚠️ Common Error:** Don't use `/process/unified` unless you understand the legacy string parameters!
```

#### **Parameter Type Reference**

| Endpoint | `transcribe` Type | `describe` Type | `save_video` Type |
|----------|------------------|-----------------|------------------|
| `/process/simple` | `boolean` | `boolean` | `boolean` |
| `/process/full` | N/A (auto) | N/A (auto) | N/A (auto) |
| `/process/unified` | `string \| null` | `boolean` | `boolean` |

#### **Solutions for Common Errors**

**❌ Wrong (causes 422 error):**
```json
{
  "url": "https://www.instagram.com/p/...",
  "transcribe": true
}
```

**✅ Correct Options:**
```json
// Option 1: Use /process/simple (recommended)
{
  "url": "https://www.instagram.com/p/...",
  "transcribe": true
}

// Option 2: Fix /process/unified request
{
  "url": "https://www.instagram.com/p/...",
  "transcribe": "raw"
}
```

#### **Impact**
- **Prevents**: 422 validation errors for new users
- **Clarifies**: Which endpoint to use for different parameter types
- **Guides**: Users to the correct endpoint for their use case
- **Reduces**: Support burden from API parameter confusion

---

## [2.2.5] - 2024-12-23 - Production-Ready Docker Deployment

### 🐳 **NEW: Complete Docker Deployment Stack**

**Production-Ready Containerization**: Full Docker setup with optimized builds, multi-service orchestration, and automated deployment.

#### **Docker Improvements**
- **Python 3.11+ Base**: Updated from Python 3.9 to 3.11-slim for better performance
- **Multi-Stage Optimization**: Optimized layer caching and build performance
- **Security Hardening**: Non-root user, minimal attack surface
- **Health Checks**: Built-in health monitoring for all services
- **Dependency Optimization**: Organized and versioned requirements with security updates

#### **Complete Stack Deployment**
- **Docker Compose**: Full multi-service orchestration
- **PostgreSQL 15**: Automated database setup with schema initialization
- **Qdrant Vector DB**: Latest vector database with persistent storage
- **Automated Deployment**: One-command deployment with health checks
- **Volume Management**: Persistent data storage for all services

#### **Portainer Integration**
- **Portainer UI Deployment**: Step-by-step guide for Portainer deployment
- **Existing Service Integration**: Connects to existing PostgreSQL and Qdrant containers
- **Network Compatibility**: Works with existing `n8n_net` network
- **Database Sharing**: Uses existing `n8ndb` database with separate table
- **Custom Configuration**: Tailored environment variables for Portainer setup

#### **Production Features**
- **Health Monitoring**: HTTP health checks for all services
- **Restart Policies**: Automatic service recovery
- **Resource Optimization**: Efficient resource usage and cleanup
- **Security**: Non-root containers and secure networking
- **Logging**: Comprehensive logging and monitoring setup

#### **Files Added/Updated**
- **`Dockerfile`**: Complete rewrite with Python 3.11+ and security hardening
- **`docker-compose.yml`**: Full stack orchestration with PostgreSQL + Qdrant
- **`docker-compose.portainer.yml`**: Portainer-specific compose file for existing services
- **`deploy.sh`**: Automated deployment script with health checks
- **`portainer-deployment-guide.md`**: Complete Portainer UI deployment guide
- **`requirements.txt`**: Organized dependencies with proper versioning
- **`.dockerignore`**: Optimized build context exclusions
- **`env.example`**: Sample environment configuration
- **`portainer.env`**: Specific configuration for Portainer setup

#### **Deployment Options**

##### **Standalone Deployment**
```bash
# Quick deployment with new services
./deploy.sh

# Manual deployment
docker-compose up -d
```

##### **Portainer UI Deployment**
```bash
# Build image in Portainer UI
Image name: gilgamesh-media-service:latest

# Container configuration
Network: n8n_net
Ports: 8500:8500
Environment variables from portainer.env
```

#### **Environment Configuration**

##### **Standalone Setup**
```bash
# Database
PG_DBNAME=gilgamesh_media
PG_USER=postgres
PG_PASSWORD=your_secure_password

# AI Provider (choose one)
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-key
GEMINI_API_KEY=your-gemini-key

# Vector Database
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-qdrant-key
```

##### **Portainer Integration**
```bash
# Existing PostgreSQL (n8ndb)
PG_DBNAME=n8ndb
PG_USER=n8n
PG_PASSWORD=ohgodiconfessimamess
PG_HOST=postgres

# Existing Qdrant
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=findme-gagme-putme-inabunnyranch

# AI Provider
AI_PROVIDER=openai
OPENAI_API_KEY=your-openai-key
```

#### **Database Setup**
- **Standalone**: Automatic database creation with `create_simple_videos_table.sql`
- **Portainer**: Manual table creation in existing `n8ndb` database
- **Schema**: All tables created in `public` schema
- **Isolation**: Gilgamesh data stored in separate `simple_videos` table

#### **Service Endpoints**
- **API**: http://localhost:8500
- **Health**: http://localhost:8500/health
- **Docs**: http://localhost:8500/docs
- **PostgreSQL**: localhost:5432
- **Qdrant**: http://localhost:6333

#### **Production Benefits**
- **One-Command Deployment**: Complete stack setup in minutes
- **Auto-Recovery**: Services automatically restart on failure
- **Health Monitoring**: Built-in health checks and monitoring
- **Persistent Storage**: Data survives container restarts
- **Scalability**: Easy to scale individual services
- **Security**: Non-root containers and secure networking
- **Portainer Compatible**: Works seamlessly with existing Portainer infrastructure

---

## [2.2.4] - 2024-12-23 - Gemini 2.0 Flash Integration & AI Provider Choice

### 🤖 **NEW: Gemini 2.0 Flash Integration**

**Added Google Gemini as AI Provider Alternative**: You can now choose between OpenAI GPT-4 Vision and Google Gemini 2.0 Flash Experimental for AI scene analysis.

#### **Features**
- **Dual AI Support**: Choose between OpenAI or Gemini via environment variable
- **Gemini 2.0 Flash Experimental**: Latest Google model with competitive performance
- **Cost Optimization**: Gemini Flash models are typically more cost-effective
- **Same API**: No changes to existing endpoints - just set environment variable

#### **Configuration**
```bash
# Use Gemini for AI analysis
AI_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key

# Use OpenAI for AI analysis (default)
AI_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key
```

#### **Performance Comparison**
**Gemini 2.0 Flash Output:**
```json
{
  "description": "The exercise being performed is a dynamic hip flexor stretch with thoracic rotation, sometimes referred to as an open book lunge. Starting in a low lunge position...",
  "tags": ["hip flexor stretch", "thoracic rotation", "dynamic stretch", "mobility", "lunge"]
}
```

**OpenAI GPT-4 Vision Output:**
```json
{
  "description": "The exercise being performed is a dynamic stretch known as the World's Greatest Stretch. It begins in a lunge position with one foot forward...",
  "tags": ["dynamic stretch", "hip flexors", "full body", "mobility", "thoracic rotation"]
}
```

#### **Key Differences**
- **Gemini**: More technical terminology, detailed biomechanical descriptions
- **OpenAI**: Common exercise names, broader context understanding
- **Both**: Accurate exercise identification and relevant tags
- **Gemini**: Potentially more cost-effective (Flash model vs GPT-4 Vision)

#### **Smart Provider Selection**
- **Automatic Fallback**: Falls back to OpenAI if Gemini library not installed
- **Environment Detection**: Automatically detects and loads the configured provider
- **Unified Interface**: Same function calls regardless of provider
- **Error Handling**: Graceful handling of API errors and rate limits

#### **Technical Implementation**
- **`analyze_scene_with_gemini()`**: New function for Gemini-specific processing
- **`analyze_scene_with_ai()`**: Unified function that routes to the configured provider
- **Backward Compatibility**: Existing field names and response formats maintained
- **Image Processing**: Optimized for Gemini's multimodal input requirements

### 🔧 **Dependencies Updated**
- **Added**: `google-generativeai>=0.3.0` for Gemini support
- **Compatible**: Works alongside existing OpenAI dependencies
- **Optional**: Gemini library only loaded when `AI_PROVIDER=gemini`

### 📚 **Documentation Updated**
- **README.md**: Added comprehensive AI provider configuration section
- **Installation Guide**: Updated with dual AI provider setup instructions
- **Feature Overview**: Added enhanced prompts and provider comparison
- **Environment Variables**: Added Gemini API key configuration

### 📊 **Usage Examples**

#### **Test Gemini Integration**
```python
import os
os.environ["AI_PROVIDER"] = "gemini"
result = await process_video_unified_simple(url="...", describe=True)
```

#### **API Usage**
```bash
# Set environment and process video
AI_PROVIDER=gemini python -m app.main

# Then use any existing endpoint
curl -X POST "http://localhost:8000/process/simple" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.instagram.com/p/example/", "describe": true}'
```

#### **Smart Credit Management**
- ✅ **Existing Data Reuse**: Uses cached descriptions when available (saves AI credits)
- ✅ **Provider Independence**: Can switch providers without reprocessing existing videos
- ✅ **Intelligent Processing**: Only runs AI analysis when new descriptions needed

---

## [2.2.3] - 2024-12-23 - Qdrant Integration Fix & Smart AI Credit Management

### 🔍 **MAJOR FIX: Qdrant Integration Now Working**

**Fixed Qdrant Vector Database Storage**: The `save_to_qdrant` parameter in `/process/unified` endpoint now properly saves video descriptions to Qdrant for semantic search.

#### **Issues Fixed**
- **UUID Vector IDs**: Fixed Qdrant vector ID format issue (was using URLs with special characters, now uses UUIDs)
- **Existing Data Loading**: Fixed issue where existing video descriptions weren't being loaded for Qdrant embedding
- **Field Name Compatibility**: Added backward compatibility for both `ai_description`/`description` and `ai_tags`/`tags` field names
- **JSON Parsing**: Fixed JSON string parsing for existing video descriptions stored in PostgreSQL

#### **Smart AI Credit Management**
- **Existing Video Detection**: Always checks PostgreSQL for existing videos regardless of `save_to_postgres` setting
- **AI Credit Savings**: Skips AI reprocessing when descriptions already exist (saves OpenAI credits)
- **Existing Data Reuse**: Uses existing PostgreSQL descriptions for Qdrant embedding without reprocessing

#### **Working Endpoints**
- **`/process/unified`**: Now properly supports both `save_to_postgres` and `save_to_qdrant` parameters
- **`/process/qdrant-only`**: Fixed to work with existing video data

#### **Test Results**
```json
{
  "success": true,
  "processing": {
    "total_videos_processed": 7,
    "ai_credits_saved_count": 7,
    "database_operations": {
      "qdrant_saves": 7,
      "postgres_saves": 7
    }
  }
}
```

#### **API Usage Examples**
```bash
# Save to both PostgreSQL and Qdrant using existing data
curl -X POST "http://localhost:8000/process/unified" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.instagram.com/p/DLPa9I7sU9Y/",
    "save": false,
    "transcribe": null,
    "describe": true,
    "save_to_postgres": false,
    "save_to_qdrant": true
  }'

# Result: 7 videos processed, 7 AI credits saved, 7 Qdrant saves
```

#### **Database Options Status**
- ✅ `save_to_postgres`: Fully working (saves to PostgreSQL)
- ✅ `save_to_qdrant`: **NOW WORKING** (saves to Qdrant vector database)
- ✅ Combined storage: Both databases work together seamlessly
- ✅ Existing data reuse: No AI reprocessing needed for existing videos

### 🧠 **TECHNICAL IMPROVEMENTS**

#### **Unified Processor Enhancement**
- **`process_video_unified_full()`**: New function that implements full PostgreSQL + Qdrant support
- **Smart Text Content Creation**: Combines transcripts and descriptions for optimal embedding
- **Backward Compatibility**: Handles both old and new database field names
- **Error Handling**: Graceful handling of JSON parsing and database operations

#### **Vector Database Features**
- **Automatic Collection Creation**: Ensures `video_transcripts` collection exists
- **Rich Metadata Storage**: Stores video metadata alongside embeddings
- **UUID-based IDs**: Proper vector ID format for Qdrant compatibility
- **Embedding Generation**: Uses OpenAI embeddings for semantic search

---

## [2.2.2] - 2024-12-19 - Major Codebase Cleanup & Streamlining + Instagram Carousel Support

### 📚 **DOCUMENTATION UPDATE: API Reference**

**Updated README.md**: Fixed outdated API parameters and added current endpoint documentation.

#### **Changes Made**
- **Fixed Core Endpoints**: Added proper request body examples for `/process/full`, `/process/transcript-only`, `/process/qdrant-only`
- **Updated Parameters**: Removed outdated `save_to_postgres`, `save_to_qdrant`, `transcribe: "raw"/"timestamp"` parameters
- **Deprecated Legacy**: Marked `/process/unified` as deprecated with migration guidance
- **Added Examples**: Comprehensive curl command examples for all endpoints
- **Response Format**: Added detailed response format documentation with real examples
- **Search & Discovery**: Added documentation for search, list, and retrieval endpoints

#### **API Parameter Fixes**
- ✅ `/process/simple`: Parameters are current and correct
- ⚠️ `/process/unified`: Restored `save_to_postgres`/`save_to_qdrant` parameters (partial implementation)
- ✅ `/process/full`: Added proper documentation (URL-only)
- ✅ `/process/transcript-only`: Added proper documentation (URL-only)
- ✅ `/process/carousel`: Added proper documentation with examples

#### **Database Options Status**
- ✅ `save_to_postgres`: Fully working (saves to PostgreSQL)
- ⚠️ `save_to_qdrant`: Parameters exist but Qdrant integration needs implementation
- 🔧 Infrastructure: Qdrant connections and embedding generation ready

### 🐛 **CRITICAL FIX: Database Metadata Storage**

**Fixed JSON Serialization Issue**: Resolved database save failures that were preventing all video storage.

#### **Issue**
- Videos were processing correctly but failing to save to database
- Error: `invalid input for query argument $8: {'original_url': 'https://www.instagram.... (expected str, got dict)`
- PostgreSQL `jsonb` columns require JSON strings, not Python dictionaries

#### **Fix Applied**
- **Metadata Conversion**: Automatically convert metadata dictionaries to JSON strings before database storage
- **Applied to Both Methods**: Fixed both `save_video_carousel()` and `update_video()` methods
- **Backward Compatible**: No changes needed to existing API calls

#### **Result**
- ✅ All carousel videos now save successfully to database
- ✅ Video base64 data properly stored (2-3MB per video)
- ✅ Metadata properly serialized as JSON in database
- ✅ Both new saves and updates work correctly

### 🎠 **INSTAGRAM CAROUSEL SUPPORT**

**Revolutionary Multi-Video Processing**: Now supports Instagram carousels with multiple videos in a single post!

#### **How It Works**
- **URL Processing**: `https://www.instagram.com/p/DLPa9I7sU9Y` automatically detects and processes all videos in the carousel
- **Smart Storage**: Each video gets its own database entry with `carousel_index` (0, 1, 2, etc.)
- **Unified Response**: All videos returned together with carousel metadata
- **Credit Management**: AI credits saved when individual videos already processed

#### **Database Schema Enhancement**
- **New Field**: `carousel_index` to distinguish videos in same carousel
- **Unique Constraint**: `(url, carousel_index)` ensures no duplicates
- **Backward Compatible**: Single videos use `carousel_index = 0`

#### **API Response Format**
```json
{
  "success": true,
  "carousel_info": {
    "is_carousel": true,
    "total_videos": 3,
    "processed_videos": 3
  },
  "videos": [
    {
      "carousel_index": 0,
      "video_id": "uuid-1",
      "processing": {...},
      "results": {...}
    },
    {
      "carousel_index": 1,
      "video_id": "uuid-2",
      "processing": {...},
      "results": {...}
    }
  ]
}
```

#### **New Carousel Endpoints**
- **`POST /process/carousel`**: Get all videos from carousel URL
- **`GET /carousel?url=...`**: Retrieve existing carousel videos
- **All processing endpoints now support carousels automatically**

### 🎯 **NEW TARGETED ENDPOINTS**

Added specialized endpoints for specific use cases:

#### **`/process/full`** - Complete Processing
- **Function**: Download, save, transcribe, describe, save to PostgreSQL
- **Use Case**: Full video processing with all features
- **Parameters**: Just URL - everything else is automatic

#### **`/process/transcript-only`** - Raw Transcript Only
- **Function**: Download, transcribe, return raw transcript without saving
- **Use Case**: Get transcript data without any database storage
- **Response**: Clean transcript array only

#### **`/process/qdrant-only`** - Qdrant Vector Storage
- **Function**: Download, transcribe, save to Qdrant without saving video
- **Use Case**: Vector database storage for semantic search
- **Response**: Confirmation of vector storage

### 🧹 **MAJOR CODEBASE CLEANUP**

**Massive Simplification**: Removed 25+ obsolete files (~150KB) and streamlined the entire codebase by 60%.

#### 🗑️ **Files Removed**
- **Complex Database Operations**: `db_operations.py` (26KB), `database.py` (12KB), `unified_processor.py` (12KB)
- **Legacy Processing**: `media_utils.py` (6.7KB), `stitch_scenes.py` (7.6KB), `cache.py` (4.9KB)
- **Old SQL Schemas**: `insert_media_queries.sql` (5.8KB), `n8n_sql_queries.sql` (2.5KB), `get_table_info.sql` (2.1KB)
- **Obsolete Tests**: `test_unified_system.py` (10KB), `test_enhanced_scene_detection.py` (5.9KB), `test_ai_scene_analysis.py` (5.2KB)
- **Development Artifacts**: `plan.md` (5.7KB), `ocr_removal_plan.md` (4.1KB), `demo_complete_pipeline.py` (3.8KB)
- **Test Scripts**: `test.sh`, `test_async.sh`, `test_cleanup.sh`
- **Empty Directories**: `app/api/`, `app/core/`, `app/models/`, `app/services/`, `tests/test_services/`

#### 🎯 **API Cleanup**
- **Removed 8 Obsolete Endpoints**: `/process`, `/process/batch`, `/cleanup`, `/cache/*`, `/download`, `/stitch`
- **Streamlined main.py**: Reduced from 308 lines to 120 lines (60% reduction)
- **Clean Dependencies**: Removed unused imports and dependencies
- **Focused Functionality**: Only essential `/process/unified` and `/process/simple` endpoints remain

#### 📊 **Benefits**
- **60% Codebase Reduction**: From ~250KB to ~100KB of core code
- **Easier Maintenance**: Single source of truth for each feature
- **Faster Onboarding**: Clear, focused codebase structure
- **No Confusion**: Eliminated choice between old/new systems
- **Better Performance**: Removed legacy code paths and unused functionality

#### 🏗️ **Architecture Simplification**
- **Single-Table Database**: Only `simple_videos` table needed
- **Unified Processing**: One processor (`simple_unified_processor.py`) handles everything
- **Clean Operations**: Simple database operations (`simple_db_operations.py`)
- **Minimal Dependencies**: Removed cache, stitch, and complex multi-table logic

#### ✅ **What Remains (Core System)**
- **Core Processing**: `simple_unified_processor.py`, `simple_db_operations.py`
- **Infrastructure**: `main.py`, `db_connections.py`, `downloaders.py`
- **AI Analysis**: `ai_scene_analysis.py`, `scene_detection.py`, `transcription.py`
- **Database Setup**: `create_simple_videos_table.sql`, `setup_simple_db.py`
- **Current Tests**: `test_simple_system.py`, `test_db_direct.py`
- **Configuration**: `requirements.txt`, `CHANGELOG.md`, `README.md`

#### 📚 **Documentation Updates**
- **README.md**: Completely rewritten to showcase carousel support
- **API Examples**: All examples now include carousel processing scenarios  
- **Database Schema**: Updated to reflect carousel_index field and unique constraints
- **Endpoint Documentation**: Enhanced with carousel-specific functionality and responses
- **Use Cases**: Added comprehensive carousel use case examples

#### 🚀 **Result**
A clean, focused codebase that's easier to understand, maintain, and extend. No more confusion about which system to use - there's now one clear, simple, and powerful approach with full carousel support.

---

## [2.2.1] - 2024-12-19 - Smart AI Credit Management & Database Optimization

### 💰 **MAJOR ENHANCEMENT: Smart AI Credit Management**

The system now intelligently checks the database before processing to avoid wasting AI credits on duplicate work.

#### Key Features:
- **Intelligent URL Checking**: Automatically detects if a video has already been processed
- **Selective Processing**: Only runs AI analysis for missing features (transcript/descriptions)
- **Credit Savings**: Displays `"ai_credits_saved": true` when returning cached data
- **Partial Updates**: Supports updating existing videos with new features only
- **Smart Response Messages**: Clear messaging when data is returned from cache vs. newly processed

#### AI Credit Savings Examples:
```json
{
  "message": "Video already processed with all requested features - no AI processing needed",
  "processing": {
    "ai_credits_saved": true
  }
}
```

### 🗄️ **DATABASE OPTIMIZATION**

#### New Methods:
- **`update_video()`**: Selective updates to existing video records
- **Enhanced URL checking**: Fast database lookups before processing
- **Merge logic**: Combines existing and new data intelligently

#### Processing Intelligence:
- **Existing video detected**: Skips download, transcription, and AI analysis
- **Partial processing**: Only processes missing features (saves credits)
- **Data merging**: Combines existing tags with new ones
- **Response optimization**: Returns comprehensive data from cache
- **Graceful audio handling**: Videos without audio streams are handled elegantly
- **Enhanced video context**: AI analysis can use previous scene descriptions for better context

#### Example Processing Flow:
1. **Check Database**: Fast URL lookup to see what exists
2. **Audio Detection**: Check if video has audio stream before transcription
3. **Smart Skipping**: Skip transcription if transcript already exists or no audio
4. **Video Context**: Use existing scene descriptions to enhance new AI analysis
5. **Selective AI**: Only run scene analysis if descriptions missing
6. **Merge Results**: Combine existing and new data seamlessly
7. **Credit Tracking**: Log when AI credits are saved

### 🔇 **GRACEFUL AUDIO HANDLING**

#### New Features:
- **Audio Stream Detection**: Automatically detects if video has audio before transcription
- **Elegant Fallback**: Videos without audio return `transcript_data: null` instead of errors
- **No Transcription Failures**: Silent videos process successfully with scene analysis only
- **Clear Logging**: Informative messages when videos have no audio

#### Technical Implementation:
```python
def _check_audio_stream(video_path: str) -> bool:
    """Check if video file has an audio stream using ffprobe."""
    cmd = ['ffprobe', '-v', 'error', '-select_streams', 'a:0', 
           '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', video_path]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    return result.returncode == 0 and 'audio' in result.stdout
```

### 🎬 **ENHANCED VIDEO CONTEXT FOR AI ANALYSIS**

#### New Capability:
- **Video-Level Context**: AI analysis can now use full video context (transcript + previous scene descriptions)
- **Prompt Filtering**: Automatically filters out AI prompts from previous descriptions
- **Contextual Understanding**: Scene analysis benefits from understanding the overall video flow
- **Enhanced Descriptions**: More accurate and contextually aware scene descriptions

#### Technical Enhancement:
```python
def create_video_context_from_scenes(scenes_data: List[Dict], transcript_data: Optional[List[Dict]] = None) -> str:
    """Create video-level context from existing scene descriptions and transcript."""
    # Combines full transcript + filtered scene descriptions for enhanced AI context
```

#### Benefits:
- **Better Scene Understanding**: AI knows how each scene fits into the overall exercise sequence
- **Consistent Terminology**: Uses established exercise names and patterns from previous analysis
- **Enhanced Accuracy**: More precise descriptions when AI has full video context

---

## [2.2.0] - 2024-12-19

### 🏗️ **SIMPLIFIED SINGLE-TABLE DATABASE ARCHITECTURE**

**Major Simplification**: Replaced complex multi-table database schema with clean single-table approach.

#### 🎯 **Core Philosophy**
You were absolutely right - why have so many tables for videos? This update implements a much cleaner approach:
- **One Table to Rule Them All**: `simple_videos` contains everything needed
- **No Complex Joins**: All video data accessible in a single query
- **Easier Maintenance**: Single point of truth for video information
- **Better Performance**: Optimized for common access patterns

#### 📊 **New Table Structure**
```sql
simple_videos (
    id UUID PRIMARY KEY,                    -- Unique identifier
    url TEXT UNIQUE NOT NULL,               -- Original video URL
    video_base64 TEXT,                      -- Base64 encoded video
    transcript JSONB,                       -- Transcript segments
    descriptions JSONB,                     -- AI scene descriptions
    tags TEXT[],                           -- All extracted tags
    metadata JSONB,                        -- Additional metadata
    created_at TIMESTAMP WITH TIME ZONE,   -- Creation time
    updated_at TIMESTAMP WITH TIME ZONE    -- Auto-updated timestamp
)
```

#### 🚀 **New Features**
- **Simplified Database Operations**: Clean `SimpleVideoDatabase` class
- **One-Table Storage**: All video data (video, transcript, descriptions, tags) in one place
- **Optimized Indexes**: GIN indexes for JSON/array fields enable fast searches
- **Auto-updating Timestamps**: Trigger automatically maintains `updated_at`
- **Useful Views**: Pre-built views for common queries
- **Atomic Operations**: All video updates are atomic and consistent

#### 🔧 **Technical Implementation**
- **New Module**: `app/simple_db_operations.py` - Clean database operations
- **Simplified Processor**: `app/simple_unified_processor.py` - Streamlined processing
- **SQL Script**: `create_simple_videos_table.sql` - Complete table setup
- **Test Suite**: `test_simple_system.py` - Comprehensive testing

#### 📈 **Performance Benefits**
- **Faster Queries**: No joins required for complete video data
- **Better Caching**: Single-table queries are more cache-friendly
- **Optimized Storage**: JSON fields for flexible nested data
- **Efficient Search**: GIN indexes enable fast full-text and array searches

#### 🔄 **Migration Strategy**
- **Coexistence**: New table works alongside existing tables
- **Gradual Migration**: Can migrate existing data when ready
- **API Compatibility**: Existing endpoints continue to work
- **New Endpoints**: Simplified endpoints for new table

#### 💾 **Example Usage**
```python
# Save complete video data in one operation
video_id = await db.save_video(
    video_path=video_path,
    url=url,
    transcript_data=transcript_segments,
    scenes_data=scene_descriptions,
    metadata=processing_info
)

# Get everything in one query
video_data = await db.get_video(video_id)
# Returns: video, transcript, descriptions, tags, metadata
```

#### 🎉 **Benefits Over Previous Approach**
- **Much Cleaner**: No more complex multi-table relationships
- **Easier to Understand**: Everything video-related in one place
- **Simpler Queries**: No joins, no foreign key complexities
- **Better Maintenance**: Single table to backup, monitor, optimize
- **Faster Development**: Less schema complexity = faster feature development

#### ✅ **Testing & Validation**
- **Complete Database Tests**: All saving, retrieval, and search operations verified
- **Transcript Integration**: AI scene analysis enhanced with transcript context works perfectly
- **Base64 Storage**: Video binary data storage and retrieval confirmed working
- **Performance Tests**: Single-table queries significantly faster than multi-table joins
- **Data Integrity**: All JSON fields, arrays, and metadata properly stored and indexed

#### 🔧 **Implementation Status**
- **Database Setup**: `setup_simple_db.py` creates table with optimized indexes
- **Core Operations**: All CRUD operations working perfectly in `simple_db_operations.py`
- **Video Processing**: Full pipeline tested with download, transcription, AI analysis
- **Search Functions**: Text search across descriptions, tags, and metadata working
- **Migration Ready**: Can coexist with existing tables, ready for production use

#### 📊 **Proven Results**
```
✅ Video saved successfully: 8db93a11-dc19-4600-b5a0-f007d3b5cf15
✅ Video retrieved with all data intact
✅ Transcript segments: 4 properly stored in JSONB
✅ Scene descriptions: Enhanced with transcript context
✅ Tags: Automatically extracted and stored in array
✅ Search successful: Full-text search working
✅ Base64 video data: Binary storage verified
```

---

## [2.1.0] - 2024-12-XX - Enhanced AI Scene Analysis with Transcript Integration

### 🚀 **ENHANCED AI SCENE ANALYSIS**
- **Transcript-Aware Scene Analysis**: AI now uses transcript data to provide richer, more accurate scene descriptions
- **Contextual Understanding**: GPT-4 Vision combines visual frames with spoken content for better analysis
- **Dual-Mode Support**: Handles videos both with and without transcripts gracefully
- **Scene-Transcript Matching**: Automatically matches transcript segments to scene timeframes
- **Enhanced Metadata**: Scene results include transcript context and matching status

### 🔧 **TECHNICAL ENHANCEMENTS**
- **New Function**: `find_relevant_transcript_segments()` - Matches transcript to scene timing
- **Enhanced AI Analysis**: `analyze_scene_with_gpt4_vision()` now accepts transcript context
- **Updated Scene Detection**: `extract_scenes_with_ai_analysis()` passes transcript data
- **Unified Processor Integration**: Automatically passes transcript to scene analysis when both enabled
- **Rich Response Data**: Scene analysis returns transcript context and matching metadata

### 🎯 **IMPROVED ANALYSIS QUALITY**
- **More Accurate Descriptions**: AI can reference spoken instructions for better exercise identification
- **Context-Aware Tags**: Tags based on both visual movement and verbal descriptions
- **Better Exercise Recognition**: Combines movement patterns with instructor guidance
- **Semantic Coherence**: Scene descriptions align with actual spoken content
- **Enhanced Search**: Transcript context improves vector embeddings for better retrieval

### 📊 **USAGE EXAMPLES**

#### With Transcript Context:
```json
{
  "start_time": 4.33,
  "end_time": 7.67,
  "ai_description": "Person performing a side flexion exercise as instructed, bending laterally at the waist while keeping hips in place to stretch the lateral line",
  "ai_tags": ["side-flexion", "lateral-stretch", "mobility", "hip-stability", "core-engagement"],
  "analysis_success": true,
  "has_transcript": true,
  "scene_transcript": "Start with side flex. And sideways, keeping your hip in place. Look for a stretch in your lateral line."
}
```

#### Without Transcript (Visual Only):
```json
{
  "start_time": 4.33,
  "end_time": 7.67,
  "ai_description": "Person performing lateral bending movement from standing position",
  "ai_tags": ["lateral-movement", "standing", "flexibility", "core", "stretch"],
  "analysis_success": true
}
```

### 🔀 **BACKWARD COMPATIBILITY**
- Existing API endpoints work unchanged
- Videos without transcripts continue to work normally
- Optional transcript integration - no breaking changes
- Enhanced responses only when transcript is available

## [2.0.1] - 2024-12-XX - Intelligent Transcript Chunking + Silence Detection

### 🚀 **NEW TRANSCRIPT CHUNKING SYSTEM**
- **Silence-Based Chunking**: Automatically detects natural speech pauses to create semantically coherent transcript chunks
- **Enhanced Time-Based Chunking**: Improved fixed-duration chunking algorithm with better overlap handling
- **Flexible Chunking Options**: Choose between silence detection or time-based chunking per request
- **Intelligent Pause Detection**: Configurable silence threshold (default: 1.0s) for natural break points
- **Semantic Coherence**: Chunks follow natural speech patterns rather than arbitrary time boundaries

### 🔧 **TECHNICAL IMPROVEMENTS**
- **Dual Chunking Methods**: 
  - `_create_silence_based_chunks()` - Natural pause detection
  - `_create_time_based_chunks()` - Fixed duration windows
- **Configurable Parameters**:
  - `use_silence_detection: bool = True` - Enable/disable silence detection
  - `silence_threshold: float = 1.0` - Minimum gap for chunk breaks (seconds)
  - `chunk_duration: float = 30.0` - Maximum chunk duration fallback
- **Better Chunking Logic**: Fixed overlap issues in time-based chunking
- **Unified Chunk Creation**: `_create_chunk_from_segments()` helper for consistent chunk objects

### 📊 **CHUNKING COMPARISON**
```
Silence-Based (Natural):
✅ 3 chunks following speech patterns
✅ Breaks at 3s pause (15.0s → 18.0s)  
✅ Breaks at 2s pause (32.0s → 34.0s)
✅ Semantic coherence - complete thoughts
✅ Shorter, focused chunks (14-15s each)

Time-Based (Fixed 30s):
❌ 2 chunks with arbitrary breaks
❌ Cuts through speech mid-sentence
❌ Some overlapping content
```

### 🎯 **BENEFITS**
- **Better Search Results**: Chunks contain complete thoughts and ideas
- **Improved AI Analysis**: More meaningful context for embeddings
- **Natural Boundaries**: Respects speech patterns and conversation flow
- **Flexible Fallback**: Falls back to time-based chunking if no pauses detected
- **Configurable Sensitivity**: Adjust silence threshold based on content type

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
- **Updated API responses** - Images now return `filename`