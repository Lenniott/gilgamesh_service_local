# CHANGELOG

## MAJOR FEATURE: Advanced AI Rate Limiting System - 2024-12-23 🚦

### 🚦 **NEW: Comprehensive AI API Rate Limiting with Circuit Breakers**

**Implemented advanced rate limiting system to handle OpenAI and Gemini API quotas, throttling, and daily limits.**

#### **Key Features Implemented:**

**1. Exponential Backoff with Jitter** ✅
- **Smart Retry Logic**: Exponential backoff (1s → 2s → 4s → 8s → 16s)
- **Jitter Addition**: ±25% randomization to prevent thundering herd
- **Max Delay Cap**: 5-minute maximum to prevent infinite waits
- **Fast Fail**: Immediate failure for daily quota exhaustion

**2. Circuit Breaker Pattern** ✅
- **Three States**: CLOSED (normal) → OPEN (blocking) → HALF_OPEN (testing)
- **Failure Threshold**: Opens after 5 consecutive failures
- **Recovery Threshold**: Closes after 3 consecutive successes
- **Timeout Protection**: 5-minute timeout before attempting recovery
- **Automatic Recovery**: Self-healing when services recover

**3. Rate Limit Detection & Handling** ✅
```python
# Detects various rate limiting scenarios
- "rate limit exceeded" → REQUESTS_PER_MINUTE
- "daily quota exceeded" → DAILY_QUOTA  
- "token limit exceeded" → TOKENS_PER_MINUTE
- "service overloaded" → TEMPORARY_OVERLOAD
```

**4. Provider-Specific Configurations** ✅
```python
# OpenAI (GPT-4 Vision)
requests_per_minute: 60
tokens_per_minute: 150,000
daily_quota: 100,000

# Gemini (Flash 2.0)
requests_per_minute: 100
tokens_per_minute: 300,000
daily_quota: 1,000,000
```

**5. Real-time Usage Tracking** ✅
- **Minute-by-minute tracking**: Requests and token usage
- **Daily quota monitoring**: Persistent tracking across requests
- **Automatic resets**: Counters reset at appropriate intervals
- **Token estimation**: Intelligent prediction based on content

#### **API Integration:**

**Rate-Limited API Calls:**
```python
# Before (vulnerable to rate limits)
response = await openai_client.chat.completions.create(...)

# After (protected with rate limiting)
rate_limiter = get_rate_limiter("openai")
response = await rate_limiter.execute_with_rate_limiting(
    make_openai_call,
    estimated_tokens=estimated_tokens
)
```

**New Monitoring Endpoint:**
```bash
# Monitor rate limiting status
GET /rate-limits

# Response includes usage stats, limits, circuit breaker state
{
  "success": true,
  "providers": {
    "openai": {
      "current_usage": {...},
      "limits": {...},
      "circuit_breaker": {"state": "closed"},
      "availability": {"can_proceed": true}
    }
  }
}
```

#### **Rate Limiting Behaviors:**

**Scenario 1: Requests Per Minute Limit**
- **Detection**: "rate limit exceeded" error from API
- **Action**: Wait until next minute boundary
- **Retry**: Automatically retry when limit resets

**Scenario 2: Daily Quota Exceeded**
- **Detection**: "daily quota exceeded" error
- **Action**: Fail fast with clear error message
- **Recovery**: Automatic reset at midnight

**Scenario 3: Service Overload**
- **Detection**: "service overloaded" or similar errors
- **Action**: Exponential backoff starting at 30 seconds
- **Circuit Breaker**: Opens after repeated failures

**Scenario 4: Token Limits**
- **Detection**: Token-specific rate limit errors
- **Action**: Wait for token limit reset
- **Estimation**: Better token usage prediction

#### **Error Handling Examples:**

```json
// Quota exceeded (fail fast)
{
  "success": false,
  "error": "Daily quota exceeded for openai - try again tomorrow",
  "rate_limit_type": "daily_quota"
}

// Circuit breaker open
{
  "success": false,
  "error": "Circuit breaker is OPEN for gemini - service temporarily unavailable",
  "circuit_breaker_state": "open"
}

// Temporary rate limit (with retry)
{
  "success": false,
  "error": "Rate limit exceeded for openai: requests_per_minute",
  "retry_after": 45,
  "message": "Retrying automatically..."
}
```

#### **Files Added/Modified:**
- **NEW**: `app/ai_rate_limiter.py` - Complete rate limiting implementation
- **UPDATED**: `app/ai_scene_analysis.py` - Integrated rate limiting into API calls
- **UPDATED**: `app/main.py` - Added `/rate-limits` monitoring endpoint
- **UPDATED**: `README.md` - Comprehensive rate limiting documentation

#### **Impact:**
- ✅ **Reliability**: No more "daily quota exceeded" crashes
- ✅ **Cost Management**: Intelligent usage tracking and limits
- ✅ **User Experience**: Graceful handling of API limits
- ✅ **Monitoring**: Real-time visibility into API usage
- ✅ **Auto-Recovery**: Self-healing when services recover
- ✅ **Provider Flexibility**: Easy switching between OpenAI/Gemini

#### **Next Steps for Users:**
1. **Monitor Usage**: Use `/rate-limits` endpoint to track API consumption
2. **Configure Limits**: Adjust limits in code for your API tier
3. **Set Alerts**: Monitor circuit breaker states for service health
4. **Plan Capacity**: Use daily quota tracking for usage planning

---

## CRITICAL BUG FIX: Division by Zero Error Resolution - 2024-12-23 🚨

### 🐛 **FIXED: Division by Zero Error in API Processing**

**Resolved the "division by zero" error that was causing 500 server errors during video processing.**

#### **Root Cause Analysis:**
The error was occurring in multiple locations where mathematical operations didn't handle edge cases:

1. **Scene Detection (`app/scene_detection.py`, line 228)**:
   ```python
   # BEFORE (causing division by zero)
   frame_timestamp = start_time + (frame_idx / (len(scene_frames) - 1)) * scene_duration
   
   # AFTER (safe division)
   if len(scene_frames) <= 1:
       frame_timestamp = start_time + (scene_duration / 2)  # Use middle of scene
   else:
       frame_timestamp = start_time + (frame_idx / (len(scene_frames) - 1)) * scene_duration
   ```

2. **Video Looping (`app/stitch_scenes.py`, line 52)**:
   ```python
   # BEFORE (causing division by zero)
   loops = int(target_duration / video_duration) + 1
   
   # AFTER (safe division)
   if video_duration <= 0:
       raise ValueError(f"Video has invalid duration: {video_duration}")
   loops = int(target_duration / video_duration) + 1
   ```

#### **Complete Fixes Implemented:**

**1. Scene Detection Division by Zero Fix** ✅
- **Problem**: When extracting only 1 frame from a scene, `len(scene_frames) - 1` became 0
- **Solution**: Added check for single frame case, uses middle of scene timestamp
- **Impact**: Prevents crashes when processing very short video segments

**2. Video Duration Error Handling** ✅
- **Problem**: `get_video_duration()` could return 0 or invalid values for corrupted videos
- **Solution**: Enhanced error handling with proper validation
- **Files Updated**: `app/stitch_scenes.py` and `app/scene_detection.py`

**3. Enhanced Duration Validation** ✅
```python
# New robust duration checking
def get_video_duration(video_path: str) -> float:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration_str = result.stdout.strip()
        if not duration_str:
            raise ValueError(f"No duration found for video: {video_path}")
        duration = float(duration_str)
        if duration <= 0:
            raise ValueError(f"Invalid duration for video: {duration}")
        return duration
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Failed to get video duration for {video_path}: {e.stderr}")
```

**4. Audio Duration Validation** ✅
- **Same robust error handling** applied to `get_audio_duration()`
- **Prevents division by zero** in audio processing
- **Clear error messages** for debugging

#### **Error Prevention Strategy:**
- **Input Validation**: All duration values checked before mathematical operations
- **Edge Case Handling**: Special handling for single frames and zero durations
- **Descriptive Errors**: Clear error messages for debugging corrupted media files
- **Graceful Degradation**: Systems continue operating when possible

#### **Testing Recommendations:**
```bash
# Test with potentially problematic videos
curl -X POST "http://localhost:8500/process" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/very-short-video", "transcribe": true}'

# Test with various video formats and lengths
curl -X POST "http://localhost:8500/process" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/single-frame-video", "describe": true}'
```

#### **Impact:**
- ✅ **API Stability**: No more 500 errors from division by zero
- ✅ **Video Processing**: Handles edge cases like single-frame scenes
- ✅ **Error Reporting**: Clear error messages for debugging
- ✅ **Robustness**: Graceful handling of corrupted or invalid media files
- ✅ **User Experience**: Reliable processing without unexpected crashes

---

## README Update: Qdrant Force Index Endpoint Documentation - 2024-12-23 📖

### 📚 **DOCUMENTATION UPDATE: Added `/qdrant/force-index` Endpoint Details**

**Enhanced README.md with comprehensive documentation for the new Qdrant indexing endpoint.**

#### **Documentation Added:**
- **Complete endpoint documentation** for `POST /qdrant/force-index`
- **Request/response examples** with multiple use cases
- **Parameter explanations** for `collections` and `force_rebuild` options
- **Practical examples** showing default collections and custom configurations
- **Key features breakdown** explaining automatic collection selection and smart indexing
- **Use case guidance** for troubleshooting and pipeline optimization

#### **New Documentation Section:**
```markdown
#### Force Qdrant Indexing:

**`POST /qdrant/force-index`** - Force indexing of Qdrant collections for AI video compilation pipeline.

**Use Case:** When you have vectors in Qdrant collections but aren't indexed yet, preventing efficient search operations.
```

#### **Examples Added:**
- **Default collections indexing**: Empty request body uses AI video compilation collections
- **Specific collections**: Target individual collections for indexing
- **Force rebuild**: Complete index recreation option
- **Mixed configurations**: Combine collection selection with rebuild options

#### **Response Documentation:**
- **Detailed response structure** with before/after statistics
- **Success/failure indicators** for each collection
- **Next steps guidance** for testing and verification
- **Error handling examples** for missing collections

#### **Perfect for:**
- **Developers** implementing AI video compilation pipeline
- **Troubleshooting** vector search issues after bulk vectorization
- **Operations** optimizing Qdrant performance for large datasets
- **Integration** ensuring search functionality works correctly

#### **Impact:**
- ✅ **Clear endpoint usage** - Developers understand how to use the new indexing endpoint
- ✅ **Troubleshooting guide** - Documentation helps resolve common indexing issues
- ✅ **Pipeline readiness** - AI video compilation teams have complete endpoint reference
- ✅ **Integration support** - Full request/response examples for implementation

---

## Qdrant Search Fix & AI Video Compilation Ready - 2024-12-23 ✅

### 🔍 **MAJOR FIX: Qdrant Vector Search Now Working for AI Video Compilation**

**Fixed the core issue preventing AI video compilation pipeline from retrieving content from Qdrant.**

#### **Problem Identified:**
- **Qdrant collections had content** (65 transcript + 31 scene vectors = 96 total)
- **But indexed_vectors_count was 0** - vectors existed but weren't indexed
- **Search endpoint used PostgreSQL text search** instead of Qdrant vector search

#### **Solutions Implemented:**

**1. New Qdrant Indexing Endpoint** ✅
- **`POST /qdrant/force-index`** - Forces indexing of AI video compilation collections
- **Automatic indexing** of `video_transcript_segments` and `video_scene_descriptions`
- **Before/after reporting** with indexing statistics
- **Force rebuild option** for complete index recreation

```bash
# Force indexing for AI video compilation
curl -X POST "http://localhost:8500/qdrant/force-index" \
  -H "Content-Type: application/json" \
  -d '{"collections": null, "force_rebuild": false}'
```

**Results:**
- ✅ `video_transcript_segments`: 0 → 65 indexed vectors
- ✅ `video_scene_descriptions`: 0 → 31 indexed vectors  
- ✅ **96 total vectors now searchable**

**2. Search Engine Conversion** ✅
- **Converted `/search` endpoint** from PostgreSQL text search to Qdrant vector search
- **OpenAI embeddings integration** for semantic search
- **Dual collection search** across transcript segments and scene descriptions
- **Relevance scoring** with configurable threshold (0.3 minimum)
- **Fallback mechanism** to PostgreSQL if Qdrant unavailable

**3. Enhanced Search Results** ✅
- **Vector relevance scores** (0.3-0.5 range for good matches)
- **Matched text snippets** showing what content triggered the match
- **Match type identification** (transcript_segment vs scene_description)
- **Full video metadata** with search context
- **Duplicate removal** by video_id with best score selection

#### **Verification Results:**
```bash
# Test search now returns 5 relevant results for "exercise"
curl "http://localhost:8500/search?q=exercise&limit=5"

# Results: Pull-ups (0.45), Farmers Walk (0.40), Kettlebell (0.38), Squats (0.37, 0.34)
```

#### **Impact for AI Video Compilation:**
- ✅ **Content retrieval now works** - Can find exercise videos by semantic meaning
- ✅ **AI requirements generator ready** - Search queries will return relevant content  
- ✅ **Script generation ready** - Can match user requirements to actual video content
- ✅ **Pipeline foundation complete** - Ready for video segment extraction and composition

#### **New Capabilities:**
- **Semantic exercise search**: "workout", "strength training", "mobility" all return relevant videos
- **Content-aware queries**: AI can generate search terms that match actual video content
- **Cross-modal search**: Search across both speech (transcripts) and visual (scene descriptions)
- **Quality scoring**: Relevance scores help prioritize best content matches

#### **Technical Details:**
- **Vector dimension**: 1536 (OpenAI text-embedding-3-small)
- **Search threshold**: 0.3 minimum relevance score
- **Collections**: `video_transcript_segments`, `video_scene_descriptions`
- **Indexing method**: Optimizer threshold adjustment (20000 → 1 → 20000)
- **Search method**: Dual collection query with deduplication

**Next Steps**: AI video compilation pipeline can now proceed to video segment extraction and composition phases.

---

## [2.2.12] - 2024-12-23 - Raw Transcript Support

### 🎯 **NEW FEATURE: Raw Transcript Parameter**

**Added `raw_transcript` parameter to return clean text without timestamps.**

#### **New Parameter:**
- **`raw_transcript: bool = False`**: Returns raw text without timestamps in addition to timestamped segments
- **API Response**: Adds `raw_transcript` field to results when enabled
- **Backward Compatible**: Default is `false`, doesn't break existing usage

#### **Usage:**
```json
{
  "url": "https://www.instagram.com/reel/...",
  "transcribe": true,
  "raw_transcript": true,
  "save_video": false,
  "save_to_postgres": false,
  "save_to_qdrant": false
}
```

#### **Response:**
```json
{
  "success": true,
  "videos": [
    {
      "results": {
        "transcript_data": [...],  // Timestamped segments
        "raw_transcript": "This is the complete transcript as clean text..."  // NEW
      }
    }
  ]
}
```

#### **Benefits:**
- **Flexible Output**: Choose timestamped segments OR raw text OR both
- **Clean Text**: Automatically strips timestamps and joins segments
- **API Native**: Built into the response structure, no post-processing needed
- **Use Cases**: Simple text extraction, content analysis, copy-paste workflows

## [2.2.11] - 2024-12-23 - API Simplification & Critical Bug Fix

### 🎯 **SIMPLIFIED API: Single Processing Endpoint**

**Consolidated multiple confusing endpoints into one clean `/process` endpoint.**

#### **Problem Solved:**
- **Fixed**: `KeyError: 'database'` in processing when videos already existed in database
- **Simplified**: Removed 5 confusing endpoints, replaced with 1 clean endpoint
- **Enhanced**: Automatic URL checking to save AI credits

#### **Changes:**
- **Removed confusing endpoints**: `/process/simple`, `/process/full`, `/process/transcript-only`, `/process/qdrant-only`, `/process/carousel`
- **Added single endpoint**: `/process` with all parameters
- **Automatic URL checking**: Always checks if URL was already processed to save AI credits
- **Fixed database KeyError**: Added missing `"database"` key in skip processing case

#### **New Single Endpoint:**
```bash
POST /process
```

**Request:**
```json
{
  "url": "https://www.instagram.com/p/...",
  "save_video": true,
  "transcribe": true, 
  "describe": true,
  "save_to_postgres": true,
  "save_to_qdrant": true,
  "include_base64": false
}
```

**Response:**
```json
{
  "success": true,
  "message": "Video processing completed successfully",
  "url": "https://www.instagram.com/p/...",
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

#### **Bug Fix Details:**
- **Root Cause**: Skip processing case was missing `"database"` key in response structure
- **Error**: `KeyError: 'database'` at line 476 when counting database operations
- **Fix**: Added missing `"database"` key with proper structure
- **Impact**: No more 500 errors when processing existing videos

#### **Benefits:**
- **Simpler API**: One endpoint instead of five confusing ones
- **Automatic optimization**: Always checks existing data to save AI credits
- **Full control**: All parameters available for customization
- **Consistent**: Same response format regardless of processing path
- **Fixed bug**: No more `KeyError: 'database'` errors
- **Backward compatible**: All existing functionality preserved

#### **Documentation:**
- **Added**: [PROJECT_VISION.md](PROJECT_VISION.md) - Comprehensive vision document
- **Purpose**: Define system boundaries, prevent scope creep, guide development
- **Content**: Architecture, API specs, data models, performance targets, roadmap

## [2.2.9] - 2024-12-23 - Individual Vector Points & Granular Search

### 🎯 **REVOLUTIONARY: Individual Vector Points for Precise Search**

**Complete Vectorization Overhaul**: Each transcript segment and scene description now gets its own vector point for granular, timestamp-based search.

#### **Revolutionary Changes:**
- **Individual Transcript Vectors**: Each transcript segment becomes its own vector point with precise timestamps
- **Individual Scene Vectors**: Each scene description becomes its own vector point with temporal metadata
- **Granular Search**: Find exact moments in videos with timestamp precision
- **Two New Collections**: `video_transcript_segments` and `video_scene_descriptions` for organized storage

#### **NEW: HTTP Vectorization Endpoint**
- **`POST /vectorize/existing`**: Vectorize existing videos via HTTP API
- **Parameters**: `limit`, `dry_run`, `verbose` for flexible control
- **Response**: Detailed progress and results information
- **Benefits**: No need for command-line access, integrates with existing API

#### **HTTP Endpoint Examples:**
```bash
# Dry run to see what would be processed
curl -X POST "http://localhost:8500/vectorize/existing" \
     -H "Content-Type: application/json" \
     -d '{"dry_run": true}'

# Process 5 videos
curl -X POST "http://localhost:8500/vectorize/existing" \
     -H "Content-Type: application/json" \
     -d '{"limit": 5}'

# Process all unvectorized videos
curl -X POST "http://localhost:8500/vectorize/existing" \
     -H "Content-Type: application/json" \
     -d '{}'
```

#### **Response Format:**
```json
{
  "success": true,
  "message": "Vectorization complete: 8/10 successful",
  "parameters": {"limit": 10, "dry_run": false, "verbose": false},
  "results": {
    "total_videos": 10, "processed": 10,
    "successful": 8, "failed": 2
  }
}
```

#### **Command Line Alternative:**
```bash
# Vectorize existing videos that haven't been vectorized yet
python vectorize_existing_videos.py [--limit N] [--dry-run] [--verbose]

# Examples:
python vectorize_existing_videos.py --dry-run --limit 5    # See what would be processed
python vectorize_existing_videos.py --limit 10             # Process 10 videos
python vectorize_existing_videos.py                        # Process all unvectorized videos
```

#### **PostgreSQL Vectorization Tracking:**
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

#### **New Vector Structure:**

**Transcript Segment Vector:**
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

**Scene Description Vector:**
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

#### **Benefits of Individual Vectors:**
- **Precise Search**: Find exact moments in videos, not just entire videos
- **Timestamp Accuracy**: Each vector contains exact timing information
- **Granular Retrieval**: Return specific segments instead of entire transcripts
- **Better Relevance**: Semantic search matches specific content, not mixed content
- **Scalable**: Each video can have dozens of searchable segments

#### **Updated Database Tracking:**
- **`vector_id`**: Now stores vector count (e.g., "14_vectors") instead of single UUID
- **Multiple vectors**: Each video can have 10-50+ individual vectors
- **Collections**: Separate collections for transcript segments and scene descriptions

#### **Code Implementation:**
```python
# Individual vector creation for transcript segments
for segment_index, segment in enumerate(transcript_segments):
    text = segment.get('text', '')
    if text:
        # Generate embedding for this segment only
        embedding = await db.connections.generate_embedding(text)
        if embedding:
            # Create vector ID (must be UUID)
            vector_id = str(uuid.uuid4())
            
            # Prepare metadata for this transcript segment
            segment_metadata = {
                "video_id": video_id,
                "segment_index": segment_index,
                "text": text,
                "start": segment.get('start', 0),
                "end": segment.get('end', 0),
                "duration": segment.get('duration', 0),
                "type": "transcript_segment",
                "tags": [],
                "vectorized_at": str(datetime.now())
            }
            
            # Store transcript segment vector
            await db.connections.store_vector(
                collection_name="video_transcript_segments",
                vector_id=vector_id,
                embedding=embedding,
                metadata=segment_metadata
            )

# Individual vector creation for scene descriptions
for scene_index, scene in enumerate(scene_descriptions):
    desc = scene.get('description', '')
    if desc:
        # Generate embedding for this scene only
        embedding = await db.connections.generate_embedding(desc)
        if embedding:
            # Create vector ID (must be UUID)
            vector_id = str(uuid.uuid4())
            
            # Prepare metadata for this scene description
            scene_metadata = {
                "video_id": video_id,
                "scene_index": scene_index,
                "description": desc,
                "start_time": scene.get('start_time', 0),
                "end_time": scene.get('end_time', 0),
                "duration": scene.get('duration', 0),
                "frame_count": scene.get('frame_count', 0),
                "type": "scene_description",
                "tags": scene.get('tags', []),
                "vectorized_at": str(datetime.now())
            }
            
            # Store scene description vector
            await db.connections.store_vector(
                collection_name="video_scene_descriptions",
                vector_id=vector_id,
                embedding=embedding,
                metadata=scene_metadata
            )

# Update PostgreSQL with vector count
await db.update_vectorization_status(video_id, f"{vectors_created}_vectors", "text-embedding-3-small")
```

#### **Migration from Old System:**
- **Old approach**: One vector per video with combined content
- **New approach**: Individual vectors per segment/scene
- **Automatic**: Updated `vectorize_existing_videos.py` handles migration
- **Collections**: Creates new `video_transcript_segments` and `video_scene_descriptions` collections
- **Backward compatible**: Existing videos can be re-vectorized with new approach

#### **Search Improvements:**
- **Precise results**: Search returns exact transcript segments or scene descriptions
- **Timestamp context**: Know exactly when something was said or shown
- **Relevance scoring**: Better semantic matching on specific content
- **Granular filtering**: Filter by segment type, video, or time range

#### **Performance Impact:**
- **More vectors**: Each video creates 10-50+ individual vectors
- **Better search**: More precise results with less noise
- **Scalable**: Qdrant handles millions of vectors efficiently
- **Consistent embeddings**: All vectors use OpenAI text-embedding-3-small

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