-- Create Video Clips Table for File-Based Storage
-- This table manages individual video clip files instead of base64 storage

-- Drop table if exists (for clean setup)
DROP TABLE IF EXISTS video_clips CASCADE;

-- Create the video_clips table
CREATE TABLE video_clips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID REFERENCES simple_videos(id) ON DELETE CASCADE,
    scene_id UUID NOT NULL,  -- UUID for the scene
    clip_path TEXT NOT NULL,  -- Path to MP4 file
    start_time FLOAT NOT NULL,  -- Start time in original video
    end_time FLOAT NOT NULL,   -- End time in original video
    duration FLOAT NOT NULL,   -- Duration of clip
    file_size BIGINT,          -- Size of clip file in bytes
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for efficient querying
CREATE INDEX idx_video_clips_video_id ON video_clips(video_id);
CREATE INDEX idx_video_clips_scene_id ON video_clips(scene_id);
CREATE INDEX idx_video_clips_path ON video_clips(clip_path);
CREATE INDEX idx_video_clips_created_at ON video_clips(created_at DESC);

-- Add new columns to existing simple_videos table
ALTER TABLE simple_videos ADD COLUMN IF NOT EXISTS video_metadata JSONB;
ALTER TABLE simple_videos ADD COLUMN IF NOT EXISTS clip_storage_version INTEGER DEFAULT 1;

-- Create index for video_metadata JSONB field
CREATE INDEX IF NOT EXISTS idx_simple_videos_video_metadata_gin ON simple_videos USING GIN(video_metadata);

-- Trigger to auto-update the updated_at timestamp for video_clips
CREATE OR REPLACE FUNCTION update_video_clips_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_video_clips_updated_at
    BEFORE UPDATE ON video_clips
    FOR EACH ROW
    EXECUTE FUNCTION update_video_clips_updated_at_column();

-- Create useful views for clip management

-- View for clip statistics
CREATE VIEW clip_stats AS
SELECT 
    vc.video_id,
    sv.url,
    sv.carousel_index,
    COUNT(vc.id) as clip_count,
    SUM(vc.file_size) as total_size_bytes,
    AVG(vc.duration) as avg_clip_duration,
    MIN(vc.created_at) as first_clip_created,
    MAX(vc.updated_at) as last_clip_updated
FROM video_clips vc
JOIN simple_videos sv ON vc.video_id = sv.id
GROUP BY vc.video_id, sv.url, sv.carousel_index;

-- View for orphaned clips (clips without corresponding videos)
CREATE VIEW orphaned_clips AS
SELECT 
    vc.id as clip_id,
    vc.clip_path,
    vc.created_at
FROM video_clips vc
LEFT JOIN simple_videos sv ON vc.video_id = sv.id
WHERE sv.id IS NULL;

-- View for video storage summary
CREATE VIEW video_storage_summary AS
SELECT 
    sv.id,
    sv.url,
    sv.carousel_index,
    CASE WHEN sv.video_base64 IS NOT NULL THEN true ELSE false END as has_base64,
    CASE WHEN sv.video_metadata IS NOT NULL THEN true ELSE false END as has_file_metadata,
    sv.clip_storage_version,
    COUNT(vc.id) as clip_count,
    SUM(vc.file_size) as total_clip_size_bytes
FROM simple_videos sv
LEFT JOIN video_clips vc ON sv.id = vc.video_id
GROUP BY sv.id, sv.url, sv.carousel_index, sv.video_base64, sv.video_metadata, sv.clip_storage_version;

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON video_clips TO your_app_user;
-- GRANT USAGE ON SCHEMA public TO your_app_user;

-- Show indexes
SELECT schemaname, tablename, indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'video_clips';

COMMENT ON TABLE video_clips IS 'File-based storage for video clips extracted from scenes';
COMMENT ON COLUMN video_clips.video_id IS 'Reference to the parent video in simple_videos';
COMMENT ON COLUMN video_clips.scene_id IS 'UUID identifier for the scene this clip belongs to';
COMMENT ON COLUMN video_clips.clip_path IS 'File system path to the MP4 clip file';
COMMENT ON COLUMN video_clips.start_time IS 'Start time of clip in original video (seconds)';
COMMENT ON COLUMN video_clips.end_time IS 'End time of clip in original video (seconds)';
COMMENT ON COLUMN video_clips.duration IS 'Duration of the clip (seconds)';
COMMENT ON COLUMN video_clips.file_size IS 'Size of the clip file in bytes'; 