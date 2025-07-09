# NEXT STEPS: Improving Retrieval Diversity and Relevance

## 1. Enforce Diversity in Retrieval
- Integrate the `optimize_search_results` method into the main pipeline.
- Set a minimum/target number of unique `video_id`s per compilation.
- After initial retrieval, re-rank or filter to maximize unique videos.

## 2. Improve Query Generation
- Make search queries more diverse by splitting user requirements into sub-goals (e.g., "mobility", "strength", "pullup progression", "handstand progression").
- Generate at least one query per sub-goal to encourage retrieval from different content.

## 3. Update Script Generator
- When building segments, explicitly avoid reusing the same `video_id` for consecutive segments.
- Enforce a hard cap on the number of segments per `video_id`.

## 4. Add Diversity Metrics and Logging
- Log the number of unique `video_id`s in each compilation.
- Warn if diversity falls below a threshold (e.g., <3 unique videos for a 10-minute routine).

## 5. (Optional) User Controls
- Allow user to specify "mix content" or "single instructor" as a preference.

## 6. Test and Validate
- Create test cases where the content exists for multiple goals (e.g., mobility, strength, pullups, handstands).
- Ensure the output compilation uses clips from multiple videos.

---

## Hypothesis Validation

- **Hypothesis:** Retrieval only returns clips from a single video post, not a true mixture.
- **Validated:** The current pipeline does not enforce diversity, and the diversity optimization logic is not used in the main flow. If the top results are from one video, all segments will be from that video.

---

## Additional Recommendations

- Consider using text-on-screen for exercise name, reps, and rounds as the primary narrative, with audio as an optional parameter.
- Simplify script generation to focus on exercise name, reps, and rounds, reducing "fluff" and improving clarity.




## Analysis: Files and Functions That Need to Be Changed

### **Hypothesis Validation**
The investigation confirms the hypothesis: **The current pipeline does not enforce diversity, and the diversity optimization logic exists but is not used in the main flow.** The `optimize_search_results` method exists in `compilation_search.py` but is never called in the main pipeline.

### **Files and Functions Requiring Changes**

#### 1. **`app/video_compilation_pipeline.py`** - **CRITICAL**
**Why:** This is the main orchestrator that calls the search engine but doesn't use diversity optimization.

**Functions to modify:**
- `process_compilation_request()` (lines ~100-200): Currently calls `search_content_segments()` directly without diversity optimization
- **Change needed:** Integrate the `optimize_search_results()` method after search but before script generation

**Specific changes:**
```python
# Current flow (line ~136):
search_results = await self.search_engine.search_content_segments(search_queries)

# New flow needed:
search_results = await self.search_engine.search_content_segments(search_queries)
# ADD: Diversity optimization step
optimized_results = await self.search_engine.optimize_search_results(
    search_results, 
    target_duration=request.max_duration,
    max_videos_per_query=3
)
```

#### 2. **`app/compilation_search.py`** - **ENHANCEMENT**
**Why:** The diversity optimization method exists but needs enhancement for better diversity enforcement.

**Functions to enhance:**
- `optimize_search_results()` (lines 358-413): Needs stronger diversity enforcement
- `search_for_compilation()` (lines 461-528): Should use diversity optimization by default
- **Add new function:** `enforce_diversity_constraints()` for hard caps on segments per video

**Enhancements needed:**
- Add minimum unique video count enforcement
- Implement hard cap on segments per `video_id` (as mentioned in nextsteps.md line 14)
- Add diversity metrics logging

#### 3. **`app/ai_requirements_generator.py`** - **IMPROVEMENT**
**Why:** To generate more diverse search queries that encourage retrieval from different content.

**Functions to enhance:**
- `generate_search_queries()` (lines 35-85): Make queries more diverse by splitting user requirements into sub-goals
- `_build_query_generation_prompt()` (lines 120-160): Enhance prompt to generate queries for different content types

**Changes needed:**
- Split user requirements into sub-goals (e.g., "mobility", "strength", "pullup progression")
- Generate at least one query per sub-goal to encourage retrieval from different content
- Add diversity-focused query generation logic

#### 4. **`app/ai_script_generator.py`** - **ENFORCEMENT**
**Why:** To enforce diversity at the script generation level and avoid reusing the same `video_id` for consecutive segments.

**Functions to modify:**
- `generate_compilation_json()` (lines 75-150): Add diversity enforcement logic
- **Add new function:** `enforce_segment_diversity()` to prevent consecutive segments from same video

**Changes needed:**
- Track used video IDs and avoid reusing for consecutive segments
- Enforce hard cap on segments per `video_id` (as mentioned in nextsteps.md)
- Add diversity validation before returning segments

#### 5. **`app/main.py`** - **LOGGING & METRICS**
**Why:** To add diversity metrics and logging for monitoring and debugging.

**Functions to enhance:**
- `/compile` endpoint (lines 219-276): Add diversity metrics to response
- **Add new endpoint:** `/compile/diversity-metrics` for monitoring diversity

**Changes needed:**
- Include diversity metrics in compilation response
- Add diversity warnings when thresholds are not met
- Log diversity statistics for monitoring

### **New Files to Create**

#### 6. **`app/diversity_manager.py`** - **NEW FILE**
**Why:** Centralized diversity management and enforcement.

**Functions to implement:**
- `enforce_diversity_constraints()`
- `calculate_diversity_metrics()`
- `validate_diversity_thresholds()`
- `log_diversity_statistics()`

### **Configuration Changes**

#### 7. **Environment Variables** - **NEW**
**Why:** Make diversity thresholds configurable.

**Add to `env.example`:**
```
# Diversity Configuration
MIN_UNIQUE_VIDEOS_PER_COMPILATION=3
MAX_SEGMENTS_PER_VIDEO=2
DIVERSITY_WARNING_THRESHOLD=0.3
```

### **Summary of Changes by Priority**

**HIGH PRIORITY (Core Functionality):**
1. `video_compilation_pipeline.py` - Integrate diversity optimization
2. `compilation_search.py` - Enhance diversity enforcement
3. `ai_script_generator.py` - Add segment-level diversity enforcement

**MEDIUM PRIORITY (Improvements):**
4. `ai_requirements_generator.py` - Generate more diverse queries
5. `main.py` - Add diversity metrics and logging

**LOW PRIORITY (Monitoring):**
6. `diversity_manager.py` - Centralized diversity management
7. Environment configuration - Configurable thresholds

The changes will ensure that:
- Each compilation uses content from multiple videos
- Hard caps are enforced on segments per video
- Diversity metrics are tracked and logged
- Users can monitor and control diversity levels
- The system warns when diversity falls below acceptable thresholds