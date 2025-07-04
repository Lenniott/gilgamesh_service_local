-- SQL queries to insert processed media JSON data into Gilgamesh tables
-- Based on actual table structure from gilgamesh_tables.csv

-- Example JSON structure we're processing:
-- {
--   "url": "https://www.youtube.com/shorts/Q-iHfObfQTU",
--   "title": "",
--   "description": "Which one are you using? Let us know in the comments...",
--   "tags": ["shorts", "chrome", "webdesign", "development"],
--   "videos": [{
--     "id": "Q-iHfObfQTU",
--     "scenes": [{
--       "start": 0.0,
--       "end": 5.0,
--       "confidence": 1.0,
--       "video": "base64-encoded-data"
--     }],
--     "transcript": [{
--       "start": 0.0,
--       "end": 5.0,
--       "text": "Transcribed audio text"
--     }]
--   }],
--   "images": [{
--     "filename": "image.jpg"
--   }]
-- }

-- 1. Insert the main social media post
INSERT INTO gilgamesh_sm_posts (
    id,
    post_url,
    generated_description,
    source_platform,
    original_description,
    created_at,
    updated_at
) VALUES (
    gen_random_uuid(),
    :url,                           -- e.g., 'https://www.youtube.com/shorts/Q-iHfObfQTU'
    :title,                         -- e.g., '' (empty in this case)
    :platform,                      -- e.g., 'youtube' (extracted from URL)
    :description,                   -- e.g., 'Which one are you using?...'
    now(),
    now()
)
ON CONFLICT (post_url) DO UPDATE SET
    generated_description = EXCLUDED.generated_description,
    original_description = EXCLUDED.original_description,
    updated_at = now()
RETURNING id;

-- 2. Insert tags into gilgamesh_sm_tags (for each tag in the tags array)
INSERT INTO gilgamesh_sm_tags (
    id,
    tag,
    created_at
) VALUES (
    gen_random_uuid(),
    :tag_name,                      -- e.g., 'shorts', 'chrome', etc.
    now()
)
ON CONFLICT (tag) DO NOTHING
RETURNING id;

-- 3. Link tags to posts in gilgamesh_sm_post_tags
INSERT INTO gilgamesh_sm_post_tags (
    post_id,
    tag_id,
    created_at
) VALUES (
    :post_id,                       -- from step 1
    :tag_id,                        -- from step 2
    now()
)
ON CONFLICT (post_id, tag_id) DO NOTHING;

-- 4. Insert videos into gilgamesh_sm_videos
INSERT INTO gilgamesh_sm_videos (
    id,
    post_id,
    video_url,
    transcript,
    created_at
) VALUES (
    gen_random_uuid(),
    :post_id,                       -- from step 1
    :video_url,                     -- could be same as post_url or specific video URL
    :full_transcript,               -- concatenated transcript from all segments
    now()
)
RETURNING id;

-- 5. Insert video scenes into gilgamesh_sm_video_scenes
INSERT INTO gilgamesh_sm_video_scenes (
    id,
    video_id,
    start_time,
    end_time,
    transcript,
    base64_snippet,
    created_at
) VALUES (
    gen_random_uuid(),
    :video_id,                      -- from step 4
    :start_time,                    -- e.g., 0.0
    :end_time,                      -- e.g., 5.0
    :scene_transcript,              -- transcript for this specific scene/time segment
    :base64_video,                  -- base64 encoded video snippet
    now()
);

-- 6. Insert images into gilgamesh_sm_images
INSERT INTO gilgamesh_sm_images (
    id,
    post_id,
    image_url,
    local_path,
    created_at
) VALUES (
    gen_random_uuid(),
    :post_id,                       -- from step 1
    :image_url,                     -- URL or path to image
    :local_file_path,               -- local file path if stored locally
    now()
);

-- 7. Update media count in gilgamesh_sm_media_count
INSERT INTO gilgamesh_sm_media_count (
    post_id,
    video_count,
    image_count,
    created_at
) VALUES (
    :post_id,                       -- from step 1
    :total_videos,                  -- count of videos processed
    :total_images,                  -- count of images processed
    now()
)
ON CONFLICT (post_id) DO UPDATE SET
    video_count = EXCLUDED.video_count,
    image_count = EXCLUDED.image_count;

-- 8. Optional: Insert into gilgamesh_content (if linking to a user)
INSERT INTO gilgamesh_content (
    id,
    user_id,
    type,
    original_url,
    transcript,
    tags,
    summary,
    created_at
) VALUES (
    gen_random_uuid(),
    :user_id,                       -- UUID of the user who processed this content
    'social_media_post',            -- content type
    :url,                           -- original URL
    :full_transcript,               -- full transcript text
    :tags_array,                    -- PostgreSQL array of tags
    :description,                   -- summary/description
    now()
);

-- Complete transaction example for the test.json data:
/*
BEGIN;

-- Variables (you'd replace these with actual values from your JSON)
-- url = 'https://www.youtube.com/shorts/Q-iHfObfQTU'
-- description = 'Which one are you using? Let us know in the comments section below...'
-- platform = 'youtube'
-- tags = ['shorts', 'chrome', 'webdesign', 'development']

-- 1. Insert post
INSERT INTO gilgamesh_sm_posts (post_url, source_platform, original_description)
VALUES ('https://www.youtube.com/shorts/Q-iHfObfQTU', 'youtube', 'Which one are you using?...')
RETURNING id; -- let's say this returns post_id = 'abc123...'

-- 2. Insert tags and link them
INSERT INTO gilgamesh_sm_tags (tag) VALUES ('shorts') ON CONFLICT (tag) DO NOTHING;
INSERT INTO gilgamesh_sm_tags (tag) VALUES ('chrome') ON CONFLICT (tag) DO NOTHING;
-- ... repeat for each tag

-- Get tag IDs and link to post
INSERT INTO gilgamesh_sm_post_tags (post_id, tag_id)
SELECT 'abc123...', id FROM gilgamesh_sm_tags WHERE tag IN ('shorts', 'chrome', 'webdesign', 'development');

-- 3. Insert video
INSERT INTO gilgamesh_sm_videos (post_id, video_url)
VALUES ('abc123...', 'https://www.youtube.com/shorts/Q-iHfObfQTU')
RETURNING id; -- let's say this returns video_id = 'def456...'

-- 4. Update media count
INSERT INTO gilgamesh_sm_media_count (post_id, video_count, image_count)
VALUES ('abc123...', 1, 0);

COMMIT;
*/ 