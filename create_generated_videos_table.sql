-- Create Generated Videos Table
-- This table stores AI-generated compilation videos with full metadata
-- Follows the same patterns as simple_videos table

-- Drop table if exists (for clean setup)
DROP TABLE IF EXISTS generated_videos CASCADE;

-- Create the main table
CREATE TABLE generated_videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,                        -- User-provided or auto-generated title
    description TEXT,                           -- Optional description
    user_requirements TEXT NOT NULL,            -- Original user context + requirements
    compilation_script JSONB NOT NULL,         -- Full script with timing and video assignments
    source_video_ids TEXT[] NOT NULL,          -- Array of source video UUIDs used
    audio_segments JSONB,                      -- Generated audio metadata and base64
    video_base64 TEXT NOT NULL,                -- Final composed video as base64
    duration FLOAT NOT NULL,                   -- Total duration in seconds
    resolution TEXT DEFAULT '720p',            -- Output resolution
    file_size INTEGER,                         -- File size in bytes
    generation_metadata JSONB,                 -- Processing details, performance metrics
    tags TEXT[],                              -- Auto-generated tags from content
    voice_model TEXT DEFAULT 'alloy',         -- OpenAI TTS voice used
    processing_time FLOAT,                    -- Total processing time in seconds
    source_videos_count INTEGER,             -- Number of source videos used
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for efficient querying
CREATE INDEX idx_generated_videos_created_at ON generated_videos(created_at DESC);
CREATE INDEX idx_generated_videos_updated_at ON generated_videos(updated_at DESC);
CREATE INDEX idx_generated_videos_duration ON generated_videos(duration);
CREATE INDEX idx_generated_videos_resolution ON generated_videos(resolution);
CREATE INDEX idx_generated_videos_voice_model ON generated_videos(voice_model);
CREATE INDEX idx_generated_videos_title ON generated_videos(title);

-- GIN indexes for JSON and array fields (for fast searching)
CREATE INDEX idx_generated_videos_script_gin ON generated_videos USING GIN(compilation_script);
CREATE INDEX idx_generated_videos_source_ids_gin ON generated_videos USING GIN(source_video_ids);
CREATE INDEX idx_generated_videos_audio_gin ON generated_videos USING GIN(audio_segments);
CREATE INDEX idx_generated_videos_metadata_gin ON generated_videos USING GIN(generation_metadata);
CREATE INDEX idx_generated_videos_tags_gin ON generated_videos USING GIN(tags);

-- Full-text search index for user requirements and title
CREATE INDEX idx_generated_videos_requirements_fulltext ON generated_videos USING GIN(to_tsvector('english', user_requirements));
CREATE INDEX idx_generated_videos_title_fulltext ON generated_videos USING GIN(to_tsvector('english', title));

-- Trigger to auto-update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_generated_videos_updated_at
    BEFORE UPDATE ON generated_videos
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create useful views for common queries

-- View for generated videos with their stats
CREATE VIEW generated_video_stats AS
SELECT 
    id,
    title,
    duration,
    resolution,
    source_videos_count,
    processing_time,
    voice_model,
    CASE WHEN video_base64 IS NOT NULL THEN true ELSE false END as has_video,
    CASE WHEN audio_segments IS NOT NULL THEN jsonb_array_length(audio_segments) ELSE 0 END as audio_segment_count,
    CASE WHEN compilation_script IS NOT NULL THEN jsonb_array_length(compilation_script->'segments') ELSE 0 END as script_segment_count,
    CASE WHEN tags IS NOT NULL THEN array_length(tags, 1) ELSE 0 END as tag_count,
    length(video_base64) as video_size_bytes,
    created_at,
    updated_at
FROM generated_videos;

-- View for compilation performance metrics
CREATE VIEW compilation_performance AS
SELECT 
    resolution,
    voice_model,
    COUNT(*) as total_compilations,
    AVG(duration) as avg_duration,
    AVG(processing_time) as avg_processing_time,
    AVG(source_videos_count) as avg_source_videos,
    AVG(processing_time / duration) as avg_processing_ratio,
    MIN(created_at) as first_compilation,
    MAX(created_at) as latest_compilation
FROM generated_videos
WHERE processing_time IS NOT NULL
GROUP BY resolution, voice_model
ORDER BY total_compilations DESC;

-- View for searchable content (combines title, requirements, and tags)
CREATE VIEW searchable_generated_content AS
SELECT 
    id,
    title,
    duration,
    resolution,
    source_videos_count,
    user_requirements,
    array_to_string(tags, ' ') as all_tags,
    to_tsvector('english', title || ' ' || user_requirements || ' ' || COALESCE(array_to_string(tags, ' '), '')) as search_vector,
    created_at
FROM generated_videos;

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON generated_videos TO your_app_user;
-- GRANT USAGE ON SCHEMA public TO your_app_user;

-- Show table info
\d generated_videos;

-- Show indexes
SELECT schemaname, tablename, indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'generated_videos'
ORDER BY indexname;

-- Show views
SELECT schemaname, viewname, definition 
FROM pg_views 
WHERE viewname LIKE '%generated%'
ORDER BY viewname;

COMMENT ON TABLE generated_videos IS 'AI-generated compilation videos with full metadata and source tracking';
COMMENT ON COLUMN generated_videos.title IS 'User-provided or auto-generated title for the compilation';
COMMENT ON COLUMN generated_videos.user_requirements IS 'Original user context and requirements that drove the compilation';
COMMENT ON COLUMN generated_videos.compilation_script IS 'JSONB containing the full script with timing, text, and video assignments';
COMMENT ON COLUMN generated_videos.source_video_ids IS 'Array of UUIDs from simple_videos table used as source material';
COMMENT ON COLUMN generated_videos.audio_segments IS 'JSONB containing generated audio metadata and base64 data';
COMMENT ON COLUMN generated_videos.video_base64 IS 'Final composed video as base64 string';
COMMENT ON COLUMN generated_videos.generation_metadata IS 'JSONB containing processing details, performance metrics, and pipeline info';
COMMENT ON COLUMN generated_videos.voice_model IS 'OpenAI TTS voice model used for audio generation';
COMMENT ON COLUMN generated_videos.processing_time IS 'Total time in seconds to generate the compilation';
COMMENT ON COLUMN generated_videos.source_videos_count IS 'Number of source videos used in the compilation'; 