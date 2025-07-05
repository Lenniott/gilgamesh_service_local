-- Create Simple Videos Table
-- This table stores all video data in a single, clean structure
-- Optimized for the simplified single-table approach

-- Drop table if exists (for clean setup)
DROP TABLE IF EXISTS simple_videos CASCADE;

-- Create the main table
CREATE TABLE simple_videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT NOT NULL,                           -- Original video URL (without img_index)
    carousel_index INTEGER DEFAULT 0,            -- Index for carousel videos (0 for single videos)
    video_base64 TEXT,                          -- Base64 encoded video data
    transcript JSONB,                           -- Transcript segments with timestamps
    descriptions JSONB,                         -- AI scene descriptions and analysis
    tags TEXT[],                               -- Extracted tags from AI analysis
    metadata JSONB,                            -- Additional metadata (source, file info, etc.)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create unique constraint for URL + carousel_index combination
CREATE UNIQUE INDEX idx_simple_videos_url_carousel ON simple_videos(url, carousel_index);

-- Create indexes for efficient querying
CREATE INDEX idx_simple_videos_url ON simple_videos(url);
CREATE INDEX idx_simple_videos_created_at ON simple_videos(created_at DESC);
CREATE INDEX idx_simple_videos_updated_at ON simple_videos(updated_at DESC);

-- GIN indexes for JSON and array fields (for fast searching)
CREATE INDEX idx_simple_videos_transcript_gin ON simple_videos USING GIN(transcript);
CREATE INDEX idx_simple_videos_descriptions_gin ON simple_videos USING GIN(descriptions);
CREATE INDEX idx_simple_videos_tags_gin ON simple_videos USING GIN(tags);
CREATE INDEX idx_simple_videos_metadata_gin ON simple_videos USING GIN(metadata);

-- Full-text search index for descriptions
CREATE INDEX idx_simple_videos_descriptions_fulltext ON simple_videos USING GIN(to_tsvector('english', descriptions::text));

-- Trigger to auto-update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_simple_videos_updated_at
    BEFORE UPDATE ON simple_videos
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create useful views for common queries

-- View for videos with their stats
CREATE VIEW video_stats AS
SELECT 
    id,
    url,
    carousel_index,
    CASE WHEN video_base64 IS NOT NULL THEN true ELSE false END as has_video,
    CASE WHEN transcript IS NOT NULL THEN jsonb_array_length(transcript) ELSE 0 END as transcript_segments,
    CASE WHEN descriptions IS NOT NULL THEN jsonb_array_length(descriptions) ELSE 0 END as scene_count,
    CASE WHEN tags IS NOT NULL THEN array_length(tags, 1) ELSE 0 END as tag_count,
    created_at,
    updated_at
FROM simple_videos;

-- View for carousel summary (grouped by URL)
CREATE VIEW carousel_summary AS
SELECT 
    url,
    COUNT(*) as video_count,
    MAX(carousel_index) + 1 as total_videos,
    MIN(created_at) as first_created,
    MAX(updated_at) as last_updated,
    bool_and(video_base64 IS NOT NULL) as all_videos_stored,
    bool_and(transcript IS NOT NULL) as all_transcribed,
    bool_and(descriptions IS NOT NULL) as all_described
FROM simple_videos
GROUP BY url;

-- View for search across all content
CREATE VIEW searchable_content AS
SELECT 
    id,
    url,
    carousel_index,
    COALESCE(
        string_agg(descriptions ->> 'description', ' '), 
        ''
    ) as all_descriptions,
    COALESCE(
        string_agg(transcript ->> 'text', ' '), 
        ''
    ) as all_transcript_text,
    array_to_string(tags, ' ') as all_tags,
    created_at
FROM simple_videos
GROUP BY id, url, carousel_index, tags, created_at;

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON simple_videos TO your_app_user;
-- GRANT USAGE ON SCHEMA public TO your_app_user;


-- Show indexes
SELECT schemaname, tablename, indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'simple_videos';

COMMENT ON TABLE simple_videos IS 'Simplified single-table storage for video content with carousel support';
COMMENT ON COLUMN simple_videos.url IS 'Original video URL without img_index parameter';
COMMENT ON COLUMN simple_videos.carousel_index IS 'Index for carousel videos: 0 for single videos, 1,2,3... for carousel items';
COMMENT ON COLUMN simple_videos.video_base64 IS 'Base64 encoded video data for storage';
COMMENT ON COLUMN simple_videos.transcript IS 'JSONB array of transcript segments with start/end times';
COMMENT ON COLUMN simple_videos.descriptions IS 'JSONB array of AI-generated scene descriptions';
COMMENT ON COLUMN simple_videos.tags IS 'Array of tags extracted from AI analysis';
COMMENT ON COLUMN simple_videos.metadata IS 'Flexible JSONB field for additional metadata'; 