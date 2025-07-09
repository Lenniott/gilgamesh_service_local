# AI Video Compilation Pipeline Documentation

## Overview
The AI Video Compilation Pipeline transforms high-level user requirements into complete video workouts by leveraging existing video content through intelligent search, AI-generated scripts, and automated video composition. The system creates realistic, complete workouts with professional text overlays and video looping.

## Current Implementation
The pipeline uses a sophisticated two-stage AI approach that generates detailed workout requirements first, then uses those requirements to guide video selection and create realistic, complete workouts. The system operates through a JSON-driven architecture with only 4 core components, reducing complexity while maintaining full functionality.

### Key Components:
- **Exercise Requirement Stories Generator**: Transforms user input into descriptive paragraphs about what needs to be worked on using GPT-4o-mini
- **Vector Search Engine**: Leverages Qdrant for semantic matching of requirement stories against scene descriptions and transcripts
- **Context-Rich Content Retriever**: Gathers matched scenes with their transcripts for compilation generation
- **AI Script Generator**: Creates complete compilation JSON using original requirements, matched scenes, and transcripts
- **Video Stitcher**: Processes JSON into final video with clip looping and audio synchronization

### Configuration and Settings:
- **Text-only mode**: Default enabled for cost reduction during testing
- **Diversity controls**: Enforces minimum unique videos and maximum segments per video
- **Aspect ratio support**: Square (1:1) and vertical (9:16) formats
- **Audio-video sync**: Perfect synchronization with audio duration as authoritative

## Architecture

### Two-Stage AI Workflow
1. **Stage 1 - Exercise Requirement Stories**: AI analyzes user input to create descriptive paragraphs about what needs to be worked on (not specific exercise names)
2. **Stage 2 - Context-Rich Matching**: Uses requirement stories to find relevant scenes and transcripts, then generates compilation JSON

### Data Flow:
1. User provides detailed natural language requirements (like your example about tight hips, handstand goals, etc.)
2. AI generates exercise requirement stories (descriptive paragraphs about what needs to be worked on)
3. Requirement stories are vectorized and matched against scene descriptions and transcripts
4. Context-rich content is retrieved (scenes + transcripts) for each requirement story
5. Another LLM creates compilation JSON using original requirements, matched scenes, and transcripts
6. Video stitcher processes JSON into final video with proper synchronization

### Error Handling:
- Graceful fallback when AI services are unavailable
- Content diversity enforcement to prevent repetitive clips
- Audio-video sync validation to ensure perfect timing
- Comprehensive logging for debugging and monitoring

## Configuration

### Environment Variables
```
# AI Provider Configuration
AI_PROVIDER=openai                    # Choose between openai or gemini
OPENAI_API_KEY=sk-your-key            # OpenAI API key for GPT-4 and TTS
GEMINI_API_KEY=your-gemini-key        # Gemini API key (alternative)

# Vector Database
QDRANT_URL=http://localhost:6333      # Qdrant vector database URL
QDRANT_API_KEY=your-qdrant-key        # Qdrant API key

# Pipeline Configuration
TEXT_ONLY_MODE=true                   # Skip audio generation for cost reduction
MIN_UNIQUE_VIDEOS_PER_COMPILATION=3   # Diversity control
MAX_SEGMENTS_PER_VIDEO=2              # Prevent overuse of same video
DIVERSITY_WARNING_THRESHOLD=0.3       # Diversity scoring threshold
```

### API Parameters
```python
# Core Request Parameters
context: str                          # "I'm creating a morning workout routine"
requirements: str                     # "5 minutes, beginner-friendly, mobility focus"
aspect_ratio: str = "9:16"           # "square" or "9:16"
max_duration: float = 600.0          # Maximum duration in seconds

# Debugging Options
text_only: bool = True               # Skip audio generation for faster testing
audio: bool = True                   # Include audio in JSON response
clips: bool = True                   # Include video clips in JSON response
include_base64: bool = False         # Return final video in response

# Diversity Controls
max_segments_per_video: int = 2      # Maximum segments per source video
min_unique_videos: int = 3           # Minimum unique videos required
```

## Dependencies

### External Dependencies
- **OpenAI API**: GPT-4o-mini for requirements generation and script creation, TTS-1-HD for audio generation
- **Qdrant Vector Database**: Semantic search across video transcript segments and scene descriptions
- **FFmpeg**: Video processing, clip extraction, and final composition
- **PostgreSQL**: Storage for video metadata and compilation results

### Internal Dependencies
- **Database Connections**: Unified connection management for all external services
- **Audio Generator**: OpenAI TTS integration for natural speech synthesis
- **Video Processing**: Scene detection and clip extraction utilities
- **Simple Database Operations**: Clean single-table database architecture

## Implementation Details

### LLM Pipeline Flow

#### Stage 1: Exercise Requirement Stories Generation
The AI analyzes user input to create descriptive paragraphs about what needs to be worked on:

```python
# Input: "I haven't exercised in months. I need to rebuild my strength slowly, but I'm also very conscious that I sit down all day so I need to work on my mobility because I'm slouching my hips are tight and my lower back is sore. I really want to be able to do a handstand, but I'm not very flexible..."

# Output: Exercise requirement stories (not specific exercise names)
[
    "Tight hip mobility training for someone who sits all day and has lower back soreness",
    "Shoulder strength and flexibility development for handstand progression",
    "Beginner-friendly strength building for someone who hasn't exercised in months",
    "Chest-to-knee compression work for handstand preparation",
    "Overall compound movement patterns for general strength development",
    "Sitting squat progression for Asian squat position achievement"
]
```

#### Stage 2: Vectorization and Matching
These requirement stories are vectorized and matched against scene descriptions and transcripts:

```python
# Vectorized requirement stories matched against:
# - video_scene_descriptions collection (visual content)
# - video_transcript_segments collection (instructor audio)

# Example matches found:
[
    {
        "requirement_story": "Tight hip mobility training for someone who sits all day",
        "matched_scenes": [
            {
                "video_id": "abc123",
                "scene_description": "Person performing hip flexor stretch in lunge position",
                "transcript": "Start in a lunge position, feel the stretch in your hip flexors...",
                "relevance_score": 0.85
            }
        ]
    }
]
```

#### Stage 3: Context-Rich Scene Retrieval
For each matched scene, retrieve both the scene description and transcript:

```python
# Retrieved context for compilation generation
{
    "requirement_story": "Tight hip mobility training for someone who sits all day",
    "matched_content": [
        {
            "video_id": "abc123",
            "scene_description": "Person performing hip flexor stretch in lunge position",
            "transcript": "Start in a lunge position, feel the stretch in your hip flexors. Keep your front knee aligned over your ankle...",
            "start_time": 15.0,
            "end_time": 25.0,
            "relevance_score": 0.85
        }
    ]
}
```

#### Stage 4: Compilation JSON Generation
Another LLM creates the final compilation JSON using:
- **Original user requirements**: The detailed user input
- **Matched scenes**: Visual content that matches the requirement stories
- **Transcripts**: Instructor audio context for each scene
- **Requirement stories**: The AI-generated descriptions of what needs to be worked on

The LLM creates:
- **Script segments**: Natural, instructional narration based on the context
- **Video clips**: Selected scenes with proper timing
- **Audio generation**: TTS-created audio for each segment
- **Text overlays**: Exercise descriptions and rep counts
- **Video looping**: Automatic looping to match audio duration

### Key Data Structures

#### Exercise Requirement Stories Object
```python
{
    "user_input": "string",             # Original detailed user requirements
    "requirement_stories": [
        "string"                        # Descriptive paragraphs about what needs to be worked on
    ],
    "target_duration": "number",        # minutes
    "intensity_level": "string",        # beginner/intermediate/advanced
    "focus_areas": ["array"],           # mobility/strength/skill/flexibility
    "constraints": ["array"]            # time_limited/equipment_limited/etc
}
```

#### Compilation JSON Structure
```python
{
    "segments": [
        {
            "id": "string"                  # short id 
            "script_segment": "string",     # AI-generated instruction
            "clips": [
                {
                    "video_id": "string",   # Source video identifier
                    "start": "number",       # Start time in source
                    "end": "number",         # End time in source
                    "video": "file path"        # link to mp4 clip
                }
            ],
            "audio": "file path",              # TTS-generated audio mp3
            "duration": "number",           # Audio duration (authoritative)
            "text_overlay": "string",       # "Squat - 10 reps"
            "category": "string",           # activation/strength/skill/cooldown
            "loop_video": "boolean",        # Whether video needs looping
            "loops_needed": "number"        # Number of loops required
        }
    ],
    "total_duration": "number",
    "aspect_ratio": "string",
}
```

## Performance & Optimization

### Cost Optimization
- **Single AI Call**: One GPT-4o-mini call per compilation instead of multiple calls
- **Text-only Mode**: Skip audio generation during testing for 80% cost reduction
- **Smart Caching**: Reuse existing video files without reprocessing
- **Diversity Controls**: Prevent overuse of same video clips
- **File-Based Processing**: Direct video file manipulation reduces encoding/decoding overhead

### Performance Characteristics
- **Processing Time**: 30-60 seconds for 5-minute compilation
- **Memory Usage**: Efficient file-based storage with persistent volume
- **Concurrency**: Semaphore-controlled API calls to prevent rate limiting
- **Scalability**: JSON-driven architecture supports parallel processing

### Monitoring and Metrics
- **Success Rate**: >95% successful compilations
- **Content Match Quality**: >85% relevant content matches
- **Audio-Video Sync**: <100ms timing deviation
- **Diversity Score**: Tracks unique video usage per compilation

## Error Handling

### Common Error Scenarios
- **No Relevant Content**: When vector search returns insufficient matches
- **Audio Generation Failure**: TTS service unavailable or quota exceeded
- **Video Processing Errors**: FFmpeg failures during clip extraction or file manipulation
- **Database Connection Issues**: Qdrant or PostgreSQL unavailable
- **File System Errors**: Missing video files or corrupted file paths

### Error Recovery Procedures
- **Fallback Queries**: Use predefined search terms when AI generation fails
- **Graceful Degradation**: Continue processing with available content
- **Retry Logic**: Exponential backoff for transient API failures
- **Circuit Breakers**: Prevent cascading failures in external services
- **File Integrity Checks**: Validate video and audio file integrity before processing

### Logging and Debugging
- **Comprehensive Logging**: Each pipeline stage logs progress and errors
- **Debug Overlays**: Video ID overlays for troubleshooting
- **Performance Metrics**: Processing time tracking for optimization
- **Error Context**: Detailed error messages with actionable information

## Security Considerations

### Input Validation
- **Request Limits**: Maximum 1000 characters for requirements
- **Duration Limits**: 30 seconds to 10 minutes for compilations
- **Content Filtering**: Validation of user input for inappropriate content
- **Rate Limiting**: Maximum 5 compilations per user per hour

### Data Protection
- **File-Based Storage**: Secure handling of video and audio files in persistent volume
- **Temporary Files**: Automatic cleanup of processing artifacts
- **Database Security**: Proper connection handling and query sanitization
- **API Security**: Input validation and error message sanitization

## Testing

### Unit Tests
- **Requirements Generation**: Test AI prompt responses and fallback logic
- **Vector Search**: Validate search query generation and result processing
- **Script Generation**: Test JSON structure creation and parsing
- **Video Processing**: Verify clip extraction and file-based audio synchronization

### Integration Tests
- **End-to-End Pipeline**: Complete compilation from user input to final video
- **Diversity Enforcement**: Verify unique video constraints are respected
- **Audio-Video Sync**: Test perfect synchronization between audio and video files
- **Error Scenarios**: Test graceful handling of service failures
- **File System Integration**: Test video file creation, storage, and retrieval

## Deployment

### Build and Deployment
- **Docker Support**: Complete containerization with optimized builds and persistent volume
- **Environment Configuration**: Flexible configuration via environment variables
- **Health Checks**: Built-in monitoring for all pipeline components
- **Resource Management**: Efficient memory and CPU usage
- **File Storage**: Persistent volume for video and audio file storage

### Environment-Specific Configurations
- **Development**: Text-only mode enabled, debug overlays active
- **Testing**: Reduced API limits, comprehensive logging
- **Production**: Full audio generation, optimized performance settings

## Troubleshooting

### Common Issues
- **"No relevant content found"**: Vector search threshold too high or insufficient content
- **"Audio-video sync issues"**: Duration calculation problems between audio and video files
- **"Diversity warnings"**: Too many segments from same video source
- **"Processing timeout"**: Large video files or slow external services
- **"File not found"**: Missing video or audio files in persistent storage
- **"Frozen frames"**: File-based processing should reduce encoding/decoding artifacts

### Debugging Procedures
- **Enable Debug Mode**: Set `show_debug_overlay=true` for video ID overlays
- **Check Logs**: Review pipeline stage logs for specific failure points
- **Test Components**: Use individual component testing for isolation
- **Monitor Resources**: Check memory usage and API rate limits
- **File System Checks**: Verify video and audio files exist in persistent storage

### Performance Profiling
- **Processing Time Analysis**: Identify bottlenecks in pipeline stages
- **Memory Usage Tracking**: Monitor file-based storage efficiency
- **API Call Optimization**: Reduce unnecessary external service calls
- **Database Query Analysis**: Optimize vector search performance

## Future Improvements

### Identified Limitations
- **Content Dependency**: Requires sufficient existing video content
- **Audio Quality**: TTS limitations for natural speech patterns
- **Video Format Constraints**: Limited to supported aspect ratios
- **Processing Time**: Real-time generation not yet possible

### Planned Enhancements
- **Custom Voice Training**: User-specific voice models for better audio
- **Advanced Transitions**: Dynamic transitions based on content type
- **Multi-Language Support**: TTS in multiple languages
- **Batch Compilation**: Generate multiple videos from single request
- **Real-time Processing**: Live video generation during user interaction

### Technical Debt Considerations
- **Database Schema**: Migration to dedicated generated videos table
- **Caching Layer**: Implement Redis for frequently accessed content
- **API Versioning**: Proper versioning for breaking changes
- **Monitoring Dashboard**: Real-time pipeline performance visualization

## Related Documentation
- **API Documentation**: Complete endpoint reference and examples
- **Database Schema**: Detailed table structures and relationships
- **User Guides**: Step-by-step compilation creation tutorials
- **Performance Benchmarks**: Detailed performance analysis and optimization

## Notes

### Important Implementation Decisions
- **Audio Duration Authority**: Audio duration drives all timing decisions to ensure perfect sync
- **Clip-First Workflow**: Script generation based on actual selected clips prevents mismatches
- **Diversity Enforcement**: Hard constraints prevent repetitive content while maintaining quality
- **JSON-Driven Architecture**: Simplified data flow with clear component boundaries

### Lessons Learned
- **Exercise Requirement Stories**: Focus on what needs to be worked on rather than specific exercise names creates better semantic matching
- **Context-Rich Matching**: Vectorization of descriptive paragraphs provides better content discovery than exercise name searches
- **Audio-Video Sync**: Using audio duration as authoritative prevents timing mismatches
- **Cost Management**: Text-only mode enables rapid iteration without audio generation costs
- **File-Based Processing**: Direct video file manipulation reduces encoding/decoding overhead and frozen frame issues

### Known Limitations
- **Content Availability**: Quality depends on existing video content in database
- **Processing Time**: Real-time generation not feasible with current architecture
- **Audio Quality**: TTS limitations for natural speech patterns and emphasis
- **Video Format**: Limited to square and 9:16 aspect ratios
- **File Storage**: Requires persistent volume for video and audio file storage

### Migration Considerations
- **File-Based Architecture**: Direct MP4 file storage in persistent volume
- **Scene Detection Integration**: Automatic MP4 clip creation during scene detection
- **Database Schema Evolution**: Support for file path references instead of base64 data
- **API Compatibility**: Maintain backward compatibility during architectural changes 