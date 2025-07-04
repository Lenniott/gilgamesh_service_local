-- Query to get table structure information for Gilgamesh tables
-- This will show column names, data types, and foreign key relationships

SELECT 
    t.table_name,
    c.column_name,
    c.data_type,
    c.character_maximum_length,
    c.is_nullable,
    c.column_default,
    CASE 
        WHEN pk.column_name IS NOT NULL THEN 'PRIMARY KEY'
        WHEN fk.column_name IS NOT NULL THEN 'FOREIGN KEY -> ' || fk.foreign_table_name || '(' || fk.foreign_column_name || ')'
        ELSE ''
    END as key_type
FROM 
    information_schema.tables t
JOIN 
    information_schema.columns c ON t.table_name = c.table_name
LEFT JOIN (
    SELECT 
        tc.table_name,
        kcu.column_name
    FROM 
        information_schema.table_constraints tc
    JOIN 
        information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
    WHERE 
        tc.constraint_type = 'PRIMARY KEY'
) pk ON c.table_name = pk.table_name AND c.column_name = pk.column_name
LEFT JOIN (
    SELECT 
        tc.table_name,
        kcu.column_name,
        ccu.table_name AS foreign_table_name,
        ccu.column_name AS foreign_column_name
    FROM 
        information_schema.table_constraints tc
    JOIN 
        information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
    JOIN 
        information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
    WHERE 
        tc.constraint_type = 'FOREIGN KEY'
) fk ON c.table_name = fk.table_name AND c.column_name = fk.column_name
WHERE 
    t.table_schema = 'public'
    AND t.table_name IN (
        'gilgamesh_content',
        'gilgamesh_mission',
        'gilgamesh_opportunities',
        'gilgamesh_opportunity_progress',
        'gilgamesh_purpose',
        'gilgamesh_sm_images',
        'gilgamesh_sm_media_count',
        'gilgamesh_sm_post_tags',
        'gilgamesh_sm_posts',
        'gilgamesh_sm_scene_exercise_metadata',
        'gilgamesh_sm_tags',
        'gilgamesh_sm_video_scenes',
        'gilgamesh_sm_videos',
        'gilgamesh_user_tags',
        'gilgamesh_users',
        'gilgamesh_values'
    )
ORDER BY 
    t.table_name, 
    c.ordinal_position; 