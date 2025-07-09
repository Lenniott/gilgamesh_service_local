# SIMPLIFIED NARRATIVE + DIVERSITY IMPROVEMENTS PLAN

## Overview
This plan addresses both the diversity improvements from `nextsteps.md` AND the additional recommendations for simplified narrative. The key insight is to implement script simplification FIRST to reduce testing costs, then add diversity enforcement.

## NEW APPROACH: Structured Script Generation

### Current Problem
The current approach generates scripts one segment at a time without considering the full context, leading to:
- Inconsistent narrative flow
- Repetitive instructions
- Higher AI costs (multiple API calls)
- Poor coordination between segments

### New Solution: Structured Script Generation
1. **Collect ALL content context** (transcripts + scene descriptions)
2. **Generate complete structured script** for entire compilation
3. **Parse structured script** into existing segment format

## Phase 1: Script Simplification (Cost Reduction - IMMEDIATE)

### Goal
Reduce AI costs by generating shorter, simpler scripts that focus only on exercise name, reps, and rounds.

### Files to Modify

#### 1. `app/ai_script_generator.py`
**NEW APPROACH:** Replace individual segment generation with structured compilation generation

**New Function:** `generate_structured_compilation_script()`
```python
async def generate_structured_compilation_script(self, 
                                               content_matches: List[ContentMatch],
                                               user_requirements: str) -> Dict[str, Any]:
    """
    Generate a complete structured script for the entire compilation.
    
    Returns structured object with:
    {
        "segments": [
            {
                "exercise_name": "Squat",
                "reps": "10",
                "rounds": "1",
                "form_cues": "feet shoulder width",
                "target_video_id": "video_123",
                "start_time": 15.0,
                "end_time": 25.0
            }
        ],
        "total_rounds": 3,
        "workout_structure": "warmup -> strength -> cooldown"
    }
    """
```

**New Function:** `collect_content_context()`
```python
async def collect_content_context(self, content_matches: List[ContentMatch]) -> Dict[str, Any]:
    """
    Collect and organize all available content context.
    
    Returns:
    {
        "video_segments": [
            {
                "video_id": "video_123",
                "start_time": 15.0,
                "end_time": 25.0,
                "scene_description": "Person doing squats with proper form",
                "transcript": "Alright, let's do some squats. Keep your feet shoulder width apart...",
                "tags": ["squat", "strength", "lower_body"]
            }
        ],
        "available_exercises": ["squat", "pushup", "plank"],
        "total_duration": 180.0
    }
    """
```

**New Function:** `parse_structured_script_to_segments()`
```python
async def parse_structured_script_to_segments(self, 
                                            structured_script: Dict[str, Any],
                                            content_matches: List[ContentMatch]) -> List[Dict[str, Any]]:
    """
    Parse the structured script into the existing segment format.
    
    Converts structured exercise data into the existing compilation JSON format.
    """
```

**Modified Function:** `generate_compilation_json()`
```python
async def generate_compilation_json(self, 
                                  content_matches: List[ContentMatch],
                                  user_requirements: str,
                                  include_audio: bool = True,
                                  include_clips: bool = True,
                                  aspect_ratio: str = "9:16",
                                  show_debug_overlay: bool = False) -> List[Dict[str, Any]]:
    """
    NEW FLOW:
    1. Collect all content context
    2. Generate structured compilation script
    3. Parse structured script to segments
    4. Add audio/clips to segments
    """
    
    # Step 1: Collect all content context
    content_context = await self.collect_content_context(content_matches)
    
    # Step 2: Generate structured compilation script
    structured_script = await self.generate_structured_compilation_script(
        content_matches, user_requirements
    )
    
    # Step 3: Parse structured script to segments
    segments = await self.parse_structured_script_to_segments(
        structured_script, content_matches
    )
    
    # Step 4: Add audio and clips
    for segment in segments:
        if include_audio:
            segment["audio"] = await self._generate_segment_audio(segment["script_segment"])
        if include_clips:
            segment["clips"] = await self._extract_clips_for_segment(segment)
    
    return segments
```

**Simplified Prompt for Structured Generation:**
```python
prompt = f"""
You are a fitness video script writer. Create a structured workout plan.

USER REQUIREMENTS: {user_requirements}

AVAILABLE CONTENT:
{content_context_summary}

Generate a JSON object with this structure:
{{
    "segments": [
        {{
            "exercise_name": "Squat",
            "reps": "10",
            "rounds": "1", 
            "form_cues": "feet shoulder width",
            "target_video_id": "video_123",
            "start_time": 15.0,
            "end_time": 25.0
        }}
    ],
    "total_rounds": 3,
    "workout_structure": "warmup -> strength -> cooldown"
}}

Rules:
- Use ONLY exercise name, reps, and rounds
- No narrative fluff
- Match exercises to available video content
- Ensure diversity across video sources
- Keep segments 10-30 seconds each
"""
```

#### 2. Add Text-on-Screen Support
**New Function:** `generate_text_overlay()`

**Purpose:** Generate exercise text for on-screen display instead of audio

```python
async def generate_text_overlay(self, structured_script: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate text overlays for each segment."""
    overlays = []
    for segment in structured_script["segments"]:
        overlay = {
            "exercise_name": segment["exercise_name"],
            "reps": segment["reps"],
            "rounds": segment["rounds"],
            "display_text": f"{segment['exercise_name']} {segment['reps']} reps"
        }
        overlays.append(overlay)
    return overlays
```

### Benefits of New Structured Approach
- **Single AI Call:** Generate entire script at once (cost reduction)
- **Better Context:** AI sees all available content
- **Consistent Flow:** Structured narrative from start to finish
- **Diversity Aware:** Can plan for video diversity at script level
- **Simplified Parsing:** Clear structure to parse into segments

## Phase 2: Diversity Enforcement (Core Functionality)

### Goal
Ensure each compilation uses content from multiple videos with hard caps on segments per video.

### Files to Modify

#### 1. `app/video_compilation_pipeline.py`
**Function:** `process_compilation_request()` (lines ~100-200)

**Add after line 136:**
```python
# Apply diversity optimization
optimized_results = await self.search_engine.optimize_search_results(
    search_results, 
    target_duration=request.max_duration,
    max_videos_per_query=3
)

# Use optimized results for script generation
content_matches = []
for result in optimized_results:
    content_matches.extend(result.matches)
```

#### 2. `app/ai_script_generator.py`
**Function:** `generate_structured_compilation_script()`

**Add diversity enforcement:**
```python
# Track used video IDs and enforce diversity
used_video_ids = set()
max_segments_per_video = 2  # Hard cap from nextsteps.md

# In structured script generation, ensure:
# - No more than max_segments_per_video per video_id
# - No consecutive segments from same video
# - Minimum unique video count
```

#### 3. `app/compilation_search.py`
**Function:** `optimize_search_results()` (lines 358-413)

**Enhancements needed:**
- Add minimum unique video count enforcement
- Implement hard cap on segments per `video_id`
- Add diversity metrics logging

## Phase 3: Testing Configuration

### Files to Modify

#### 1. `app/main.py`
**Function:** `/compile` endpoint (lines 219-276)

**Add new parameters:**
```python
class CompileRequest(BaseModel):
    # ... existing fields ...
    text_only: bool = True  # Default to text-only for cost reduction
    max_segments_per_video: int = 2  # Diversity control
    min_unique_videos: int = 3  # Diversity control
```

#### 2. `env.example`
**Add new environment variables:**
```
# Script Generation (Cost Reduction)
TEXT_ONLY_MODE=true
SCRIPT_MAX_TOKENS=200  # Single call for entire script
STRUCTURED_SCRIPT_MODE=true

# Diversity Configuration
MIN_UNIQUE_VIDEOS_PER_COMPILATION=3
MAX_SEGMENTS_PER_VIDEO=2
DIVERSITY_WARNING_THRESHOLD=0.3
```

## Implementation Order

### Step 1: Structured Script Generation (Immediate)
1. Implement `collect_content_context()`
2. Implement `generate_structured_compilation_script()`
3. Implement `parse_structured_script_to_segments()`
4. Modify `generate_compilation_json()` to use new flow
5. Test with structured generation

### Step 2: Diversity Integration (Core)
1. Integrate `optimize_search_results()` in pipeline
2. Add diversity enforcement in structured script generation
3. Add diversity metrics and logging

### Step 3: Testing & Validation (Verification)
1. Test with structured script generation
2. Validate diversity improvements
3. Monitor costs and performance

## Expected Outcomes

### Cost Reduction
- **Before:** Multiple API calls (one per segment) + audio generation
- **After:** Single API call for entire script + optional text-only mode
- **Savings:** ~80% reduction in AI costs for testing

### Diversity Improvement
- **Before:** All segments from single video
- **After:** 3+ unique videos per compilation
- **Enforcement:** Max 2 segments per video, no consecutive same video

### Testing Efficiency
- **Before:** Expensive multiple API calls for each test
- **After:** Fast single API call for rapid iteration
- **Metrics:** Clear diversity statistics for validation

## Success Metrics

### Phase 1 Success Criteria
- [ ] Single API call generates entire compilation script
- [ ] Structured script includes exercise name, reps, and rounds only
- [ ] Text-only mode works without audio generation
- [ ] Token usage reduced by 80%
- [ ] Testing costs reduced significantly

### Phase 2 Success Criteria
- [ ] Each compilation uses 3+ unique videos
- [ ] No more than 2 segments per video
- [ ] No consecutive segments from same video
- [ ] Diversity metrics are logged and tracked

### Overall Success Criteria
- [ ] Compilations are more diverse and interesting
- [ ] Testing is faster and cheaper
- [ ] Scripts are clearer and more direct
- [ ] System warns when diversity is low

## Next Steps

1. **Start with Step 1** - Structured script generation for immediate cost reduction
2. **Test thoroughly** with structured generation
3. **Implement Step 2** - Diversity enforcement
4. **Validate improvements** with real compilations
5. **Update CHANGELOG.md** with all changes

This structured approach ensures we get maximum cost savings while building toward the diversity improvements, making the entire process more efficient and affordable to test. 