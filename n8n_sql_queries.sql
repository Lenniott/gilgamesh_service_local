-- N8N WORKFLOW SQL QUERIES
-- Stage 1: Insert main post and return IDs

-- 1. INSERT MAIN POST (First stage)
INSERT INTO gilgamesh_sm_posts (
    post_url,
    generated_description,
    source_platform,
    original_description
) VALUES (
    {{ $json.result.url }},
    {{ $json.result.title }},
    'instagram',
    {{ $json.result.description }}
)
ON CONFLICT (post_url) DO UPDATE SET
    generated_description = EXCLUDED.generated_description,
    original_description = EXCLUDED.original_description,
    updated_at = now()
RETURNING id as post_id;

-- ===========================================
-- STAGE 2: LOOP QUERIES (Use in separate n8n nodes)
-- ===========================================

-- 2. INSERT TAG (Use in loop for each tag)
INSERT INTO gilgamesh_sm_tags (
    id,
    tag,
    created_at
) VALUES (
    gen_random_uuid(),
    '{{ $json.tag }}',
    now()
)
ON CONFLICT (tag) DO NOTHING
RETURNING id as tag_id;

-- 3. LINK TAG TO POST (Use after each tag insert)
INSERT INTO gilgamesh_sm_post_tags (
    post_id,
    tag_id,
    created_at
) VALUES (
    '{{ $json.post_id }}',
    '{{ $json.tag_id }}',
    now()
)
ON CONFLICT (post_id, tag_id) DO NOTHING;

-- 4. INSERT VIDEO (Use in loop for each video)
INSERT INTO gilgamesh_sm_videos (
    id,
    post_id,
    video_url,
    transcript,
    created_at
) VALUES (
    gen_random_uuid(),
    '{{ $json.post_id }}',
    '{{ $json.result.url }}',
    '{{ $json.video.transcript }}',
    now()
)
RETURNING id as video_id;

-- 5. INSERT VIDEO SCENE (Use in loop for each scene)
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
    '{{ $json.video_id }}',
    {{ $json.scene.start }},
    {{ $json.scene.end }},
    '{{ $json.scene.transcript }}',
    '{{ $json.scene.video }}',
    now()
);

-- 6. INSERT IMAGE (Use in loop for each image)
INSERT INTO gilgamesh_sm_images (
    id,
    post_id,
    image_url,
    local_path,
    created_at
) VALUES (
    gen_random_uuid(),
    '{{ $json.post_id }}',
    NULL,
    NULL,
    now()
);

-- 7. UPDATE MEDIA COUNT (Final stage after all loops)
INSERT INTO gilgamesh_sm_media_count (
    post_id,
    video_count,
    image_count,
    created_at
) VALUES (
    '{{ $json.post_id }}',
    {{ $json.video_count }},
    {{ $json.image_count }},
    now()
)
ON CONFLICT (post_id) DO UPDATE SET
    video_count = EXCLUDED.video_count,
    image_count = EXCLUDED.image_count; 