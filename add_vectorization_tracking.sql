-- Add vectorization tracking to simple_videos table
-- This allows PostgreSQL to track what has been vectorized in Qdrant

-- Add new columns for vectorization tracking
ALTER TABLE simple_videos 
ADD COLUMN vectorized_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN vector_id TEXT,
ADD COLUMN embedding_model TEXT DEFAULT 'text-embedding-3-small';

-- Create index for vectorization queries
CREATE INDEX idx_simple_videos_vectorized_at ON simple_videos(vectorized_at);
CREATE INDEX idx_simple_videos_vector_id ON simple_videos(vector_id);

-- Update the video_stats view to include vectorization info
DROP VIEW IF EXISTS video_stats;
CREATE VIEW video_stats AS
SELECT 
    id,
    url,
    carousel_index,
    CASE WHEN video_base64 IS NOT NULL THEN true ELSE false END as has_video,
    CASE WHEN transcript IS NOT NULL THEN jsonb_array_length(transcript) ELSE 0 END as transcript_segments,
    CASE WHEN descriptions IS NOT NULL THEN jsonb_array_length(descriptions) ELSE 0 END as scene_count,
    CASE WHEN tags IS NOT NULL THEN array_length(tags, 1) ELSE 0 END as tag_count,
    CASE WHEN vectorized_at IS NOT NULL THEN true ELSE false END as is_vectorized,
    vectorized_at,
    vector_id,
    embedding_model,
    created_at,
    updated_at
FROM simple_videos;

-- Update carousel_summary view to include vectorization stats
DROP VIEW IF EXISTS carousel_summary;
CREATE VIEW carousel_summary AS
SELECT 
    url,
    COUNT(*) as video_count,
    MAX(carousel_index) + 1 as total_videos,
    MIN(created_at) as first_created,
    MAX(updated_at) as last_updated,
    bool_and(video_base64 IS NOT NULL) as all_videos_stored,
    bool_and(transcript IS NOT NULL) as all_transcribed,
    bool_and(descriptions IS NOT NULL) as all_described,
    bool_and(vectorized_at IS NOT NULL) as all_vectorized,
    COUNT(*) FILTER (WHERE vectorized_at IS NOT NULL) as vectorized_count
FROM simple_videos
GROUP BY url;

-- Add comments for new columns
COMMENT ON COLUMN simple_videos.vectorized_at IS 'Timestamp when video was successfully vectorized in Qdrant';
COMMENT ON COLUMN simple_videos.vector_id IS 'UUID of the vector stored in Qdrant';
COMMENT ON COLUMN simple_videos.embedding_model IS 'OpenAI model used for embedding generation';

-- Show the updated schema
\d simple_videos; 