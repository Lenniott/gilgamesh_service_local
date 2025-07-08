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
- Optionally, enforce a hard cap on the number of segments per `video_id`.

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
