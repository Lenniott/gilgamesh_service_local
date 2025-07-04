-- SQL queries to insert processed media JSON data into Gilgamesh tables
-- Using the exact variable references from your template syntax

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
    '{{ $json.result.url }}',                    -- Post URL
    '{{ $json.result.title }}',                  -- Generated/Title description
    'youtube',                                   -- Hardcoded for now, or extract from URL logic
    '{{ $json.result.description }}',            -- Original description
    now(),
    now()
)
ON CONFLICT (post_url) DO UPDATE SET
    generated_description = EXCLUDED.generated_description,
    original_description = EXCLUDED.original_description,
    updated_at = now()
RETURNING id;

-- 2. Insert tags into gilgamesh_sm_tags (for each tag in the tags array)
-- This needs to be done in a loop for each tag in {{ $json.result.tags }}
INSERT INTO gilgamesh_sm_tags (
    id,
    tag,
    created_at
) VALUES (
    gen_random_uuid(),
    '{{ $json.result.tags[INDEX] }}',            -- Replace INDEX with actual array index (0, 1, 2, etc.)
    now()
)
ON CONFLICT (tag) DO NOTHING
RETURNING id;

-- 3. Link tags to posts in gilgamesh_sm_post_tags
-- This also needs to be done for each tag
INSERT INTO gilgamesh_sm_post_tags (
    post_id,
    tag_id,
    created_at
) VALUES (
    (SELECT id FROM gilgamesh_sm_posts WHERE post_url = '{{ $json.result.url }}'),  -- Get post_id
    (SELECT id FROM gilgamesh_sm_tags WHERE tag = '{{ $json.result.tags[INDEX] }}'), -- Get tag_id
    now()
)
ON CONFLICT (post_id, tag_id) DO NOTHING;

-- 4. Insert videos into gilgamesh_sm_videos
-- This needs to be done for each video (though you seem to have only [0])
INSERT INTO gilgamesh_sm_videos (
    id,
    post_id,
    video_url,
    transcript,
    created_at
) VALUES (
    gen_random_uuid(),
    (SELECT id FROM gilgamesh_sm_posts WHERE post_url = '{{ $json.result.url }}'),  -- Get post_id
    '{{ $json.result.url }}',                    -- Using same URL, or could be specific video URL
    '{{ $json.result.videos[0].transcript }}',   -- Full transcript array as text
    now()
)
RETURNING id;

-- 5. Insert video scenes into gilgamesh_sm_video_scenes
-- This needs to be done for each scene in {{ $json.result.videos[0].scenes }}
-- Scene [0]:
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
    (SELECT v.id FROM gilgamesh_sm_videos v 
     JOIN gilgamesh_sm_posts p ON v.post_id = p.id 
     WHERE p.post_url = '{{ $json.result.url }}'),           -- Get video_id
    {{ $json.result.videos[0].scenes[0].start }},            -- Start time
    {{ $json.result.videos[0].scenes[0].end }},              -- End time
    NULL,                                                     -- Scene-specific transcript (if available)
    '{{ $json.result.videos[0].scenes[0].video }}',          -- Base64 video snippet
    now()
);

-- Scene [1] (if exists):
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
    (SELECT v.id FROM gilgamesh_sm_videos v 
     JOIN gilgamesh_sm_posts p ON v.post_id = p.id 
     WHERE p.post_url = '{{ $json.result.url }}'),           -- Get video_id
    {{ $json.result.videos[0].scenes[1].start }},            -- Start time
    {{ $json.result.videos[0].scenes[1].end }},              -- End time
    NULL,                                                     -- Scene-specific transcript
    '{{ $json.result.videos[0].scenes[1].video }}',          -- Base64 video snippet
    now()
);

-- 6. Insert images into gilgamesh_sm_images (if images exist)
-- This needs to be done for each image in {{ $json.result.images }}
INSERT INTO gilgamesh_sm_images (
    id,
    post_id,
    image_url,
    local_path,
    created_at
) VALUES (
    gen_random_uuid(),
    (SELECT id FROM gilgamesh_sm_posts WHERE post_url = '{{ $json.result.url }}'),  -- Get post_id
    NULL,                                        -- No image URL in your JSON structure
    NULL,                                        -- No local path in your JSON structure
    now()
);

-- 7. Update media count in gilgamesh_sm_media_count
INSERT INTO gilgamesh_sm_media_count (
    post_id,
    video_count,
    image_count,
    created_at
) VALUES (
    (SELECT id FROM gilgamesh_sm_posts WHERE post_url = '{{ $json.result.url }}'),  -- Get post_id
    1,                                           -- Assuming 1 video (adjust based on actual count)
    CASE WHEN '{{ $json.result.images }}' != '' THEN 1 ELSE 0 END,  -- 1 if images exist, 0 otherwise
    now()
)
ON CONFLICT (post_id) DO UPDATE SET
    video_count = EXCLUDED.video_count,
    image_count = EXCLUDED.image_count;

-- EXAMPLE: Complete transaction for your JSON structure
/*
BEGIN;

-- 1. Insert main post
INSERT INTO gilgamesh_sm_posts (post_url, generated_description, source_platform, original_description)
VALUES ('{{ $json.result.url }}', '{{ $json.result.title }}', 'youtube', '{{ $json.result.description }}');

-- 2. Insert tags (you'd need to loop through {{ $json.result.tags }})
INSERT INTO gilgamesh_sm_tags (tag) VALUES ('{{ $json.result.tags[0] }}') ON CONFLICT (tag) DO NOTHING;
INSERT INTO gilgamesh_sm_tags (tag) VALUES ('{{ $json.result.tags[1] }}') ON CONFLICT (tag) DO NOTHING;
-- ... continue for each tag

-- 3. Link tags to post
INSERT INTO gilgamesh_sm_post_tags (post_id, tag_id)
SELECT p.id, t.id 
FROM gilgamesh_sm_posts p, gilgamesh_sm_tags t 
WHERE p.post_url = '{{ $json.result.url }}' 
AND t.tag IN (SELECT unnest(ARRAY['{{ $json.result.tags[0] }}', '{{ $json.result.tags[1] }}']));

-- 4. Insert video
INSERT INTO gilgamesh_sm_videos (post_id, video_url, transcript)
SELECT id, '{{ $json.result.url }}', '{{ $json.result.videos[0].transcript }}'
FROM gilgamesh_sm_posts WHERE post_url = '{{ $json.result.url }}';

-- 5. Insert scenes
INSERT INTO gilgamesh_sm_video_scenes (video_id, start_time, end_time, base64_snippet)
SELECT v.id, {{ $json.result.videos[0].scenes[0].start }}, {{ $json.result.videos[0].scenes[0].end }}, 
       '{{ $json.result.videos[0].scenes[0].video }}'
FROM gilgamesh_sm_videos v 
JOIN gilgamesh_sm_posts p ON v.post_id = p.id 
WHERE p.post_url = '{{ $json.result.url }}';

-- 6. Update media count
INSERT INTO gilgamesh_sm_media_count (post_id, video_count, image_count)
SELECT id, 1, 0 FROM gilgamesh_sm_posts WHERE post_url = '{{ $json.result.url }}';

COMMIT;
*/ 