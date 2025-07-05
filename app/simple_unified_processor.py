#!/usr/bin/env python3
"""
Simplified Unified Video Processing using single table approach.
Much cleaner than the complex multi-table approach.
"""

import os
import json
import logging
import asyncio
import base64
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from app.downloaders import download_media_and_metadata
from app.transcription import transcribe_audio
from app.scene_detection import extract_scenes_with_ai_analysis
from app.simple_db_operations import SimpleVideoDatabase
# Utils not needed for simplified approach

logger = logging.getLogger(__name__)

def normalize_url(url: str) -> str:
    """
    Normalize URL by removing img_index and other carousel-specific parameters.
    
    Args:
        url: Original URL (may contain ?img_index=N)
        
    Returns:
        Clean URL without carousel parameters
    """
    # Remove img_index and other parameters
    if '?' in url:
        base_url = url.split('?')[0]
    else:
        base_url = url
    
    # Remove trailing slash
    return base_url.rstrip('/')

async def process_video_unified_simple(
    url: str,
    save_video: bool = True,
    transcribe: bool = True,
    describe: bool = True,
    save_to_postgres: bool = True,
    save_to_qdrant: bool = True,
    include_base64: bool = False
) -> Dict[str, Any]:
    """
    Simplified unified video processing with carousel support.
    
    Args:
        url: Video URL to process (carousel URLs will process all videos)
        save_video: Whether to save video base64 to database
        transcribe: Whether to generate transcript
        describe: Whether to generate scene descriptions
        save_to_postgres: Whether to save to PostgreSQL database
        save_to_qdrant: Whether to save to Qdrant vector database
        include_base64: Whether to include base64 in response (warning: large!)
        
    Returns:
        Unified response with all processing results
    """
    download_result = None
    
    try:
        # Setup
        logging.basicConfig(level=logging.INFO)
        
        # Normalize URL (remove img_index parameters)
        normalized_url = normalize_url(url)
        logger.info(f"🔗 Normalized URL: {normalized_url}")
        
        # Create fresh database instance
        db = SimpleVideoDatabase()
        await db.initialize()
        
        # Download all videos from URL (handles carousels automatically)
        logger.info(f"📥 Downloading media from: {url}")
        download_result = await download_media_and_metadata(url)
        
        # Get all video files from download
        video_files = [f for f in download_result['files'] if f.lower().endswith(('.mp4', '.mkv', '.webm'))]
        if not video_files:
            return {
                "success": False,
                "error": "No video files found after download",
                "url": url
            }
        
        logger.info(f"✅ Found {len(video_files)} video(s) to process")
        
        # Process each video in the carousel
        processed_videos = []
        all_video_ids = []
        
        for carousel_index, video_path in enumerate(video_files):
            logger.info(f"🎬 Processing video {carousel_index + 1}/{len(video_files)}: {os.path.basename(video_path)}")
            
            # Check if this specific carousel video already exists
            existing_video = None
            if db.connections and db.connections.pg_pool:
                try:
                    existing_video = await db.get_video_by_url_and_index(normalized_url, carousel_index)
                    if existing_video:
                        logger.info(f"📁 Carousel video {carousel_index} already exists: {existing_video['id']}")
                        
                        # Check what we already have
                        has_video = existing_video["has_video"]
                        has_transcript = bool(existing_video.get('transcript'))
                        has_descriptions = bool(existing_video.get('descriptions'))
                        
                        logger.info(f"🔍 Existing data for video {carousel_index}: video={has_video}, transcript={has_transcript}, descriptions={has_descriptions}")
                        
                        # If we have everything requested, skip processing (SAVE AI CREDITS!)
                        if (not save_video or has_video) and (not transcribe or has_transcript) and (not describe or has_descriptions):
                            logger.info(f"💰 Carousel video {carousel_index} already fully processed - AI credits saved!")
                            
                            processed_videos.append({
                                "carousel_index": carousel_index,
                                "video_id": existing_video["id"],
                                "processing": {
                                    "ai_credits_saved": True,
                                    "transcription": has_transcript,
                                    "scene_analysis": has_descriptions
                                },
                                "results": {
                                    "transcript_data": existing_video.get('transcript'),
                                    "scenes_data": existing_video.get('descriptions'),
                                    "tags": existing_video.get('tags', [])
                                }
                            })
                            all_video_ids.append(existing_video["id"])
                            continue
                        
                        # Update processing flags based on what we already have
                        current_save_video = save_video and not has_video
                        current_transcribe = transcribe and not has_transcript
                        current_describe = describe and not has_descriptions
                        
                        if not current_save_video:
                            logger.info(f"💾 Video {carousel_index} already saved - skipping video save")
                        if not current_transcribe:
                            logger.info(f"🎤 Video {carousel_index} transcript exists - skipping transcription (AI credits saved!)")
                        if not current_describe:
                            logger.info(f"🎬 Video {carousel_index} descriptions exist - skipping AI analysis (AI credits saved!)")
                    else:
                        # New video, process with original flags
                        current_save_video = save_video
                        current_transcribe = transcribe
                        current_describe = describe
                        
                except Exception as e:
                    logger.warning(f"Failed to check existing video {carousel_index}: {e}")
                    current_save_video = save_video
                    current_transcribe = transcribe
                    current_describe = describe
            else:
                current_save_video = save_video
                current_transcribe = transcribe
                current_describe = describe
            
            # Initialize results for this video
            transcript_data = None
            scenes_data = None
            video_id = None
            
            # Transcription
            if current_transcribe:
                logger.info(f"🎤 Starting transcription for video {carousel_index}...")
                transcript_data = await asyncio.to_thread(transcribe_audio, video_path)
                
                if transcript_data:
                    logger.info(f"✅ Transcription completed for video {carousel_index}: {len(transcript_data)} segments")
                else:
                    logger.info(f"🔇 No transcript data for video {carousel_index} - video may not have audio")
                    transcript_data = None
            
            # Scene Analysis
            if current_describe:
                logger.info(f"🎬 Starting scene analysis for video {carousel_index}...")
                import tempfile
                with tempfile.TemporaryDirectory() as out_dir:
                    # Get existing scenes for video context if available
                    existing_scenes_for_context = None
                    if existing_video and existing_video.get('descriptions'):
                        existing_scenes_for_context = existing_video['descriptions']
                        logger.info(f"📚 Using existing scene descriptions for video {carousel_index} context: {len(existing_scenes_for_context)} scenes")
                    
                    scenes_data = await extract_scenes_with_ai_analysis(
                        video_path, 
                        out_dir,
                        transcript_data=transcript_data if current_transcribe else None,
                        existing_scenes=existing_scenes_for_context
                    )
                    
                    if scenes_data:
                        logger.info(f"✅ Scene analysis completed for video {carousel_index}: {len(scenes_data)} scenes")
                        # Log transcript context usage
                        scenes_with_transcript = sum(1 for scene in scenes_data if scene.get("has_transcript"))
                        scenes_with_video_context = sum(1 for scene in scenes_data if scene.get("has_video_context"))
                        if scenes_with_transcript > 0:
                            logger.info(f"📝 {scenes_with_transcript} scenes enhanced with transcript context for video {carousel_index}")
                        if scenes_with_video_context > 0:
                            logger.info(f"🎬 {scenes_with_video_context} scenes enhanced with video context for video {carousel_index}")
                    else:
                        logger.warning(f"⚠️ Scene analysis failed for video {carousel_index}")
            
            # Save to database (PostgreSQL)
            if save_to_postgres and (current_save_video or current_transcribe or current_describe) and db.connections and db.connections.pg_pool:
                logger.info(f"💾 Saving video {carousel_index} to PostgreSQL...")
                
                # Prepare metadata
                metadata = {
                    "original_url": url,
                    "normalized_url": normalized_url,
                    "carousel_info": {
                        "is_carousel": len(video_files) > 1,
                        "carousel_index": carousel_index,
                        "total_videos": len(video_files)
                    },
                    "processing_options": {
                        "save_video": current_save_video,
                        "transcribe": current_transcribe,
                        "describe": current_describe
                    },
                    "file_info": {
                        "path": str(video_path),
                        "size": os.path.getsize(video_path),
                        "filename": os.path.basename(video_path)
                    },
                    "download_info": {
                        "source": download_result.get('source'),
                        "description": download_result.get('description', ''),
                        "original_tags": download_result.get('tags', [])
                    }
                }
                
                try:
                    if existing_video:
                        # Update existing video with new data
                        logger.info(f"🔄 Updating existing video {carousel_index}: {existing_video['id']}")
                        video_id = await db.update_video(
                            video_id=existing_video["id"],
                            video_path=video_path if current_save_video else None,
                            transcript_data=transcript_data,
                            scenes_data=scenes_data,
                            metadata=metadata
                        )
                        if video_id:
                            logger.info(f"✅ Video {carousel_index} updated in database: {video_id}")
                        else:
                            logger.warning(f"⚠️ Failed to update video {carousel_index} in database")
                    else:
                        # Save new video
                        video_id = await db.save_video_carousel(
                            video_path=video_path,
                            url=normalized_url,
                            carousel_index=carousel_index,
                            transcript_data=transcript_data,
                            scenes_data=scenes_data,
                            metadata=metadata
                        )
                        
                        if video_id:
                            logger.info(f"✅ Video {carousel_index} saved to database: {video_id}")
                        else:
                            logger.warning(f"⚠️ Failed to save video {carousel_index} to database")
                except Exception as e:
                    logger.error(f"❌ Database save failed for video {carousel_index}: {e}")
                    video_id = None
            elif not save_to_postgres:
                logger.info(f"⏭️ Skipping PostgreSQL save for video {carousel_index} (save_to_postgres=false)")
            else:
                logger.warning(f"⚠️ PostgreSQL not available, skipping save for video {carousel_index}")
            
                                        # Save to Qdrant (NEW: Added Qdrant support to simple processor)
            qdrant_saved = False
            if save_to_qdrant and db.connections and db.connections.qdrant_client and db.connections.openai_client:
                logger.info(f"🔍 Saving video {carousel_index} to Qdrant...")
                
                try:
                    # Ensure collections exist
                    transcript_collection = "video_transcript_segments"
                    scene_collection = "video_scene_descriptions"
                    await db.connections.ensure_collection_exists(transcript_collection)
                    await db.connections.ensure_collection_exists(scene_collection)
                    
                    vectors_created = 0
                    
                    # Process transcript segments individually (current or existing)
                    transcript_for_embedding = transcript_data or (existing_video.get('transcript') if existing_video else None)
                    if transcript_for_embedding:
                        if isinstance(transcript_for_embedding, list):
                            for segment_index, segment in enumerate(transcript_for_embedding):
                                text = segment.get('text', '')
                                if text:
                                    # Generate embedding for this segment only
                                    embedding = await db.connections.generate_embedding(text)
                                    if embedding:
                                        # Create vector ID for this segment
                                        import uuid
                                        vector_id = str(uuid.uuid4())
                                        
                                        # Prepare metadata for this transcript segment
                                        segment_metadata = {
                                            "video_id": video_id or f"temp_{carousel_index}",
                                            "segment_index": segment_index,
                                            "text": text,
                                            "start": segment.get('start', 0),
                                            "end": segment.get('end', 0),
                                            "duration": segment.get('duration', 0),
                                            "url": normalized_url,
                                            "carousel_index": carousel_index,
                                            "type": "transcript_segment",
                                            "tags": [],  # Individual segments don't have tags
                                            "created_at": str(datetime.now()),
                                            "vectorized_at": str(datetime.now())
                                        }
                                        
                                        # Store transcript segment vector
                                        success = await db.connections.store_vector(
                                            collection_name=transcript_collection,
                                            vector_id=vector_id,
                                            embedding=embedding,
                                            metadata=segment_metadata
                                        )
                                        
                                        if success:
                                            vectors_created += 1
                                            logger.debug(f"✅ Created transcript segment vector {segment_index} for video {carousel_index}")
                                        else:
                                            logger.warning(f"⚠️ Failed to store transcript segment {segment_index} for video {carousel_index}")
                    
                    # Process scene descriptions individually (current or existing)
                    scenes_for_embedding = scenes_data or (existing_video.get('descriptions') if existing_video else None)
                    if scenes_for_embedding:
                        # Handle case where descriptions might be stored as JSON string
                        if isinstance(scenes_for_embedding, str):
                            import json
                            try:
                                scenes_for_embedding = json.loads(scenes_for_embedding)
                            except:
                                scenes_for_embedding = []
                        
                        for scene_index, scene in enumerate(scenes_for_embedding):
                            # Try both field names for backward compatibility
                            desc = scene.get('ai_description', '') or scene.get('description', '')
                            if desc:
                                # Generate embedding for this scene only
                                embedding = await db.connections.generate_embedding(desc)
                                if embedding:
                                    # Create vector ID for this scene
                                    import uuid
                                    vector_id = str(uuid.uuid4())
                                    
                                    # Prepare metadata for this scene description
                                    scene_metadata = {
                                        "video_id": video_id or f"temp_{carousel_index}",
                                        "scene_index": scene_index,
                                        "description": desc,
                                        "start_time": scene.get('start_time', 0),
                                        "end_time": scene.get('end_time', 0),
                                        "duration": scene.get('duration', 0),
                                        "frame_count": scene.get('frame_count', 0),
                                        "url": normalized_url,
                                        "carousel_index": carousel_index,
                                        "type": "scene_description",
                                        "tags": scene.get('ai_tags', []) or scene.get('tags', []),
                                        "created_at": str(datetime.now()),
                                        "vectorized_at": str(datetime.now())
                                    }
                                    
                                    # Store scene description vector
                                    success = await db.connections.store_vector(
                                        collection_name=scene_collection,
                                        vector_id=vector_id,
                                        embedding=embedding,
                                        metadata=scene_metadata
                                    )
                                    
                                    if success:
                                        vectors_created += 1
                                        logger.debug(f"✅ Created scene description vector {scene_index} for video {carousel_index}")
                                    else:
                                        logger.warning(f"⚠️ Failed to store scene description {scene_index} for video {carousel_index}")
                    
                    # Check if we created any vectors
                    if vectors_created > 0:
                        logger.info(f"✅ Video {carousel_index} saved to Qdrant: {vectors_created} vectors created")
                        qdrant_saved = True
                        
                        # Update PostgreSQL with vectorization info
                        if video_id and db.connections and db.connections.pg_pool:
                            try:
                                await db.update_vectorization_status(video_id, f"{vectors_created}_vectors", "text-embedding-3-small")
                                logger.info(f"✅ Updated PostgreSQL with vectorization info for video {carousel_index}")
                            except Exception as e:
                                logger.warning(f"⚠️ Failed to update vectorization status in PostgreSQL: {e}")
                    else:
                        logger.info(f"ℹ️ No vectors created for video {carousel_index} - no valid content found")
                        
                except Exception as e:
                    logger.error(f"❌ Qdrant save failed for video {carousel_index}: {e}")
            elif not save_to_qdrant:
                logger.info(f"⏭️ Skipping Qdrant save for video {carousel_index} (save_to_qdrant=false)")
            elif not db.connections.qdrant_client:
                logger.warning(f"⚠️ Qdrant client not available for video {carousel_index}")
            elif not db.connections.openai_client:
                logger.warning(f"⚠️ OpenAI client not available for embeddings for video {carousel_index}")
            
            # Prepare response for this video
            all_tags = set()
            final_transcript_data = transcript_data
            final_scenes_data = scenes_data
            
            # If we have existing video, merge data
            if existing_video:
                video_id = existing_video["id"]  # Use existing video ID
                
                # Use existing data if we didn't process new data
                if not transcript_data and existing_video.get('transcript'):
                    final_transcript_data = existing_video['transcript']
                if not scenes_data and existing_video.get('descriptions'):
                    final_scenes_data = existing_video['descriptions']
                
                # Merge tags from existing video
                if existing_video.get('tags'):
                    all_tags.update(existing_video['tags'])
            
            # Add new tags
            if scenes_data:
                for scene in scenes_data:
                    scene_tags = scene.get("ai_tags", [])
                    all_tags.update(scene_tags)
            
            video_result = {
                "carousel_index": carousel_index,
                "video_id": video_id,
                "processing": {
                    "transcription": bool(final_transcript_data),
                    "scene_analysis": bool(final_scenes_data),
                    "used_existing_data": bool(existing_video),
                    "ai_credits_saved": bool(existing_video and not (transcript_data or scenes_data))
                },
                "results": {
                    "transcript_data": final_transcript_data,
                    "scenes_data": final_scenes_data,
                    "tags": list(all_tags)
                },
                "database": {
                    "postgres_saved": bool(video_id),
                    "qdrant_saved": qdrant_saved,
                    "video_stored": bool(existing_video and existing_video["has_video"]) if existing_video else bool(current_save_video and video_id)
                }
            }
            
            # Include base64 if requested
            if include_base64 and video_id and db.connections and db.connections.pg_pool:
                try:
                    video_base64 = await db.get_video_base64(video_id)
                    video_result["results"]["video_base64"] = video_base64
                except Exception as e:
                    logger.warning(f"Failed to get video base64 for video {carousel_index}: {e}")
            
            processed_videos.append(video_result)
            if video_id:
                all_video_ids.append(video_id)
        
        # Prepare final response
        is_carousel = len(video_files) > 1
        total_credits_saved = sum(1 for v in processed_videos if v["processing"].get("ai_credits_saved", False))
        postgres_saves = sum(1 for v in processed_videos if v["database"].get("postgres_saved", False))
        qdrant_saves = sum(1 for v in processed_videos if v["database"].get("qdrant_saved", False))
        
        response = {
            "success": True,
            "message": f"{'Carousel' if is_carousel else 'Video'} processing completed successfully",
            "url": url,
            "normalized_url": normalized_url,
            "carousel_info": {
                "is_carousel": is_carousel,
                "total_videos": len(video_files),
                "processed_videos": len(processed_videos)
            },
            "processing": {
                "download": True,
                "total_videos_processed": len(processed_videos),
                "ai_credits_saved_count": total_credits_saved,
                "database_operations": {
                    "postgres_enabled": save_to_postgres,
                    "qdrant_enabled": save_to_qdrant,
                    "postgres_saves": postgres_saves,
                    "qdrant_saves": qdrant_saves
                }
            },
            "videos": processed_videos,
            "video_ids": all_video_ids
        }
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Processing failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "url": url
        }
    
    finally:
        # Cleanup temp files
        try:
            if download_result and download_result.get('temp_dir'):
                import shutil
                shutil.rmtree(download_result['temp_dir'], ignore_errors=True)
        except:
            pass

async def process_video_unified_full(
    url: str,
    save_video: bool = True,
    transcribe: bool = True,
    describe: bool = True,
    save_to_postgres: bool = True,
    save_to_qdrant: bool = True,
    include_base64: bool = False
) -> Dict[str, Any]:
    """
    Full unified video processing with PostgreSQL and Qdrant support.
    
    Args:
        url: Video URL to process (carousel URLs will process all videos)
        save_video: Whether to save video base64 to database
        transcribe: Whether to generate transcript
        describe: Whether to generate scene descriptions
        save_to_postgres: Whether to save to PostgreSQL database
        save_to_qdrant: Whether to save to Qdrant vector database
        include_base64: Whether to include base64 in response (warning: large!)
        
    Returns:
        Unified response with all processing results
    """
    download_result = None
    
    try:
        # Setup
        logging.basicConfig(level=logging.INFO)
        
        # Normalize URL (remove img_index parameters)
        normalized_url = normalize_url(url)
        logger.info(f"🔗 Normalized URL: {normalized_url}")
        
        # Create fresh database instance
        db = SimpleVideoDatabase()
        await db.initialize()
        
        # Download all videos from URL (handles carousels automatically)
        logger.info(f"📥 Downloading media from: {url}")
        download_result = await download_media_and_metadata(url)
        
        # Get all video files from download
        video_files = [f for f in download_result['files'] if f.lower().endswith(('.mp4', '.mkv', '.webm'))]
        if not video_files:
            return {
                "success": False,
                "error": "No video files found after download",
                "url": url
            }
        
        logger.info(f"✅ Found {len(video_files)} video(s) to process")
        
        # Process each video in the carousel
        processed_videos = []
        all_video_ids = []
        
        for carousel_index, video_path in enumerate(video_files):
            logger.info(f"🎬 Processing video {carousel_index + 1}/{len(video_files)}: {os.path.basename(video_path)}")
            
            # Check if this specific carousel video already exists (regardless of save_to_postgres setting)
            existing_video = None
            if db.connections and db.connections.pg_pool:
                try:
                    existing_video = await db.get_video_by_url_and_index(normalized_url, carousel_index)
                    if existing_video:
                        logger.info(f"📁 Carousel video {carousel_index} already exists: {existing_video['id']}")
                        
                        # Check what we already have
                        has_video = existing_video["has_video"]
                        has_transcript = bool(existing_video.get('transcript'))
                        has_descriptions = bool(existing_video.get('descriptions'))
                        
                        logger.info(f"🔍 Existing data for video {carousel_index}: video={has_video}, transcript={has_transcript}, descriptions={has_descriptions}")
                        
                        # If we have everything requested for processing, skip AI processing (SAVE AI CREDITS!)
                        # But still allow database operations (PostgreSQL/Qdrant) if requested
                        skip_ai_processing = (not transcribe or has_transcript) and (not describe or has_descriptions)
                        skip_video_save = (not save_video or has_video)
                        
                        if skip_ai_processing and skip_video_save and not save_to_qdrant:
                            # Complete skip - nothing new to do
                            logger.info(f"💰 Carousel video {carousel_index} already fully processed - AI credits saved!")
                            
                            processed_videos.append({
                                "carousel_index": carousel_index,
                                "video_id": existing_video["id"],
                                "processing": {
                                    "ai_credits_saved": True,
                                    "transcription": has_transcript,
                                    "scene_analysis": has_descriptions
                                },
                                "results": {
                                    "transcript_data": existing_video.get('transcript'),
                                    "scenes_data": existing_video.get('descriptions'),
                                    "tags": existing_video.get('tags', [])
                                },
                                "database": {
                                    "postgres_saved": True,
                                    "qdrant_saved": False,  # We'd need to check Qdrant too
                                    "video_stored": has_video
                                }
                            })
                            all_video_ids.append(existing_video["id"])
                            continue
                        
                        # Update processing flags based on what we already have
                        current_save_video = save_video and not has_video
                        current_transcribe = transcribe and not has_transcript
                        current_describe = describe and not has_descriptions
                        
                        if not current_save_video:
                            logger.info(f"💾 Video {carousel_index} already saved - skipping video save")
                        if not current_transcribe:
                            logger.info(f"🎤 Video {carousel_index} transcript exists - skipping transcription (AI credits saved!)")
                        if not current_describe:
                            logger.info(f"🎬 Video {carousel_index} descriptions exist - skipping AI analysis (AI credits saved!)")
                    else:
                        # New video, process with original flags
                        current_save_video = save_video
                        current_transcribe = transcribe
                        current_describe = describe
                        
                except Exception as e:
                    logger.warning(f"Failed to check existing video {carousel_index}: {e}")
                    current_save_video = save_video
                    current_transcribe = transcribe
                    current_describe = describe
            else:
                current_save_video = save_video
                current_transcribe = transcribe
                current_describe = describe
            
            # Initialize results for this video
            transcript_data = None
            scenes_data = None
            video_id = None
            
            # Transcription
            if current_transcribe:
                logger.info(f"🎤 Starting transcription for video {carousel_index}...")
                transcript_data = await asyncio.to_thread(transcribe_audio, video_path)
                
                if transcript_data:
                    logger.info(f"✅ Transcription completed for video {carousel_index}: {len(transcript_data)} segments")
                else:
                    logger.info(f"🔇 No transcript data for video {carousel_index} - video may not have audio")
                    transcript_data = None
            
            # Scene Analysis
            if current_describe:
                logger.info(f"🎬 Starting scene analysis for video {carousel_index}...")
                import tempfile
                with tempfile.TemporaryDirectory() as out_dir:
                    # Get existing scenes for video context if available
                    existing_scenes_for_context = None
                    if existing_video and existing_video.get('descriptions'):
                        existing_scenes_for_context = existing_video['descriptions']
                        logger.info(f"📚 Using existing scene descriptions for video {carousel_index} context: {len(existing_scenes_for_context)} scenes")
                    
                    scenes_data = await extract_scenes_with_ai_analysis(
                        video_path, 
                        out_dir,
                        transcript_data=transcript_data if current_transcribe else None,
                        existing_scenes=existing_scenes_for_context
                    )
                    
                    if scenes_data:
                        logger.info(f"✅ Scene analysis completed for video {carousel_index}: {len(scenes_data)} scenes")
                        # Log transcript context usage
                        scenes_with_transcript = sum(1 for scene in scenes_data if scene.get("has_transcript"))
                        scenes_with_video_context = sum(1 for scene in scenes_data if scene.get("has_video_context"))
                        if scenes_with_transcript > 0:
                            logger.info(f"📝 {scenes_with_transcript} scenes enhanced with transcript context for video {carousel_index}")
                        if scenes_with_video_context > 0:
                            logger.info(f"🎬 {scenes_with_video_context} scenes enhanced with video context for video {carousel_index}")
                    else:
                        logger.warning(f"⚠️ Scene analysis failed for video {carousel_index}")
            
            # Database Operations
            postgres_saved = False
            qdrant_saved = False
            
            # Save to PostgreSQL
            if save_to_postgres and (current_save_video or current_transcribe or current_describe) and db.connections and db.connections.pg_pool:
                logger.info(f"💾 Saving video {carousel_index} to PostgreSQL...")
                
                # Prepare metadata
                metadata = {
                    "original_url": url,
                    "normalized_url": normalized_url,
                    "carousel_info": {
                        "is_carousel": len(video_files) > 1,
                        "carousel_index": carousel_index,
                        "total_videos": len(video_files)
                    },
                    "processing_options": {
                        "save_video": current_save_video,
                        "transcribe": current_transcribe,
                        "describe": current_describe,
                        "save_to_postgres": save_to_postgres,
                        "save_to_qdrant": save_to_qdrant
                    },
                    "file_info": {
                        "path": str(video_path),
                        "size": os.path.getsize(video_path),
                        "filename": os.path.basename(video_path)
                    },
                    "download_info": {
                        "source": download_result.get('source'),
                        "description": download_result.get('description', ''),
                        "original_tags": download_result.get('tags', [])
                    }
                }
                
                try:
                    if existing_video:
                        # Update existing video with new data
                        logger.info(f"🔄 Updating existing video {carousel_index}: {existing_video['id']}")
                        video_id = await db.update_video(
                            video_id=existing_video["id"],
                            video_path=video_path if current_save_video else None,
                            transcript_data=transcript_data,
                            scenes_data=scenes_data,
                            metadata=metadata
                        )
                        if video_id:
                            logger.info(f"✅ Video {carousel_index} updated in PostgreSQL: {video_id}")
                            postgres_saved = True
                        else:
                            logger.warning(f"⚠️ Failed to update video {carousel_index} in PostgreSQL")
                    else:
                        # Save new video
                        video_id = await db.save_video_carousel(
                            video_path=video_path,
                            url=normalized_url,
                            carousel_index=carousel_index,
                            transcript_data=transcript_data,
                            scenes_data=scenes_data,
                            metadata=metadata
                        )
                        
                        if video_id:
                            logger.info(f"✅ Video {carousel_index} saved to PostgreSQL: {video_id}")
                            postgres_saved = True
                        else:
                            logger.warning(f"⚠️ Failed to save video {carousel_index} to PostgreSQL")
                except Exception as e:
                    logger.error(f"❌ PostgreSQL save failed for video {carousel_index}: {e}")
                    video_id = None
            elif not save_to_postgres:
                logger.info(f"⏭️ Skipping PostgreSQL save for video {carousel_index} (save_to_postgres=false)")
            
            # Save to Qdrant
            if save_to_qdrant and db.connections and db.connections.qdrant_client:
                logger.info(f"🔍 Saving video {carousel_index} to Qdrant...")
                
                try:
                    # Ensure collections exist
                    transcript_collection = "video_transcript_segments"
                    scene_collection = "video_scene_descriptions"
                    await db.connections.ensure_collection_exists(transcript_collection)
                    await db.connections.ensure_collection_exists(scene_collection)
                    
                    vectors_created = 0
                    
                    # Process transcript segments individually (current or existing)
                    transcript_for_embedding = transcript_data or (existing_video.get('transcript') if existing_video else None)
                    if transcript_for_embedding:
                        if isinstance(transcript_for_embedding, list):
                            for segment_index, segment in enumerate(transcript_for_embedding):
                                text = segment.get('text', '')
                                if text:
                                    # Generate embedding for this segment only
                                    embedding = await db.connections.generate_embedding(text)
                                    if embedding:
                                        # Create vector ID for this segment
                                        import uuid
                                        vector_id = str(uuid.uuid4())
                                        
                                        # Prepare metadata for this transcript segment
                                        segment_metadata = {
                                            "video_id": video_id or f"temp_{carousel_index}",
                                            "segment_index": segment_index,
                                            "text": text,
                                            "start": segment.get('start', 0),
                                            "end": segment.get('end', 0),
                                            "duration": segment.get('duration', 0),
                                            "url": normalized_url,
                                            "carousel_index": carousel_index,
                                            "type": "transcript_segment",
                                            "tags": [],  # Individual segments don't have tags
                                            "created_at": str(datetime.now()),
                                            "vectorized_at": str(datetime.now())
                                        }
                                        
                                        # Store transcript segment vector
                                        success = await db.connections.store_vector(
                                            collection_name=transcript_collection,
                                            vector_id=vector_id,
                                            embedding=embedding,
                                            metadata=segment_metadata
                                        )
                                        
                                        if success:
                                            vectors_created += 1
                                            logger.debug(f"✅ Created transcript segment vector {segment_index} for video {carousel_index}")
                                        else:
                                            logger.warning(f"⚠️ Failed to store transcript segment {segment_index} for video {carousel_index}")
                    
                    # Process scene descriptions individually (current or existing)
                    scenes_for_embedding = scenes_data or (existing_video.get('descriptions') if existing_video else None)
                    if scenes_for_embedding:
                        # Handle case where descriptions might be stored as JSON string
                        if isinstance(scenes_for_embedding, str):
                            import json
                            try:
                                scenes_for_embedding = json.loads(scenes_for_embedding)
                            except:
                                scenes_for_embedding = []
                        
                        for scene_index, scene in enumerate(scenes_for_embedding):
                            # Try both field names for backward compatibility
                            desc = scene.get('ai_description', '') or scene.get('description', '')
                            if desc:
                                # Generate embedding for this scene only
                                embedding = await db.connections.generate_embedding(desc)
                                if embedding:
                                    # Create vector ID for this scene
                                    import uuid
                                    vector_id = str(uuid.uuid4())
                                    
                                    # Prepare metadata for this scene description
                                    scene_metadata = {
                                        "video_id": video_id or f"temp_{carousel_index}",
                                        "scene_index": scene_index,
                                        "description": desc,
                                        "start_time": scene.get('start_time', 0),
                                        "end_time": scene.get('end_time', 0),
                                        "duration": scene.get('duration', 0),
                                        "frame_count": scene.get('frame_count', 0),
                                        "url": normalized_url,
                                        "carousel_index": carousel_index,
                                        "type": "scene_description",
                                        "tags": scene.get('ai_tags', []) or scene.get('tags', []),
                                        "created_at": str(datetime.now()),
                                        "vectorized_at": str(datetime.now())
                                    }
                                    
                                    # Store scene description vector
                                    success = await db.connections.store_vector(
                                        collection_name=scene_collection,
                                        vector_id=vector_id,
                                        embedding=embedding,
                                        metadata=scene_metadata
                                    )
                                    
                                    if success:
                                        vectors_created += 1
                                        logger.debug(f"✅ Created scene description vector {scene_index} for video {carousel_index}")
                                    else:
                                        logger.warning(f"⚠️ Failed to store scene description {scene_index} for video {carousel_index}")
                    
                    # Check if we created any vectors
                    if vectors_created > 0:
                        logger.info(f"✅ Video {carousel_index} saved to Qdrant: {vectors_created} vectors created")
                        qdrant_saved = True
                        
                        # Update PostgreSQL with vectorization info
                        if video_id and db.connections and db.connections.pg_pool:
                            try:
                                await db.update_vectorization_status(video_id, f"{vectors_created}_vectors", "text-embedding-3-small")
                                logger.info(f"✅ Updated PostgreSQL with vectorization info for video {carousel_index}")
                            except Exception as e:
                                logger.warning(f"⚠️ Failed to update vectorization status in PostgreSQL: {e}")
                    else:
                        logger.info(f"ℹ️ No vectors created for video {carousel_index} - no valid content found")
                        
                except Exception as e:
                    logger.error(f"❌ Qdrant save failed for video {carousel_index}: {e}")
            elif not save_to_qdrant:
                logger.info(f"⏭️ Skipping Qdrant save for video {carousel_index} (save_to_qdrant=false)")
            elif not db.connections.qdrant_client:
                logger.warning(f"⚠️ Qdrant client not available for video {carousel_index}")
            
            # Prepare response for this video
            all_tags = set()
            final_transcript_data = transcript_data
            final_scenes_data = scenes_data
            
            # If we have existing video, merge data
            if existing_video:
                if not video_id:
                    video_id = existing_video["id"]  # Use existing video ID
                
                # Use existing data if we didn't process new data
                if not transcript_data and existing_video.get('transcript'):
                    final_transcript_data = existing_video['transcript']
                if not scenes_data and existing_video.get('descriptions'):
                    final_scenes_data = existing_video['descriptions']
                
                # Merge tags from existing video
                if existing_video.get('tags'):
                    all_tags.update(existing_video['tags'])
            
            # Add new tags
            if scenes_data:
                for scene in scenes_data:
                    scene_tags = scene.get("ai_tags", [])
                    all_tags.update(scene_tags)
            
            video_result = {
                "carousel_index": carousel_index,
                "video_id": video_id,
                "processing": {
                    "transcription": bool(final_transcript_data),
                    "scene_analysis": bool(final_scenes_data),
                    "used_existing_data": bool(existing_video),
                    "ai_credits_saved": bool(existing_video and not (transcript_data or scenes_data))
                },
                "results": {
                    "transcript_data": final_transcript_data,
                    "scenes_data": final_scenes_data,
                    "tags": list(all_tags)
                },
                "database": {
                    "postgres_saved": postgres_saved or bool(existing_video),
                    "qdrant_saved": qdrant_saved,
                    "video_stored": bool(existing_video and existing_video["has_video"]) if existing_video else bool(current_save_video and video_id)
                }
            }
            
            # Include base64 if requested
            if include_base64 and video_id and db.connections and db.connections.pg_pool:
                try:
                    video_base64 = await db.get_video_base64(video_id)
                    video_result["results"]["video_base64"] = video_base64
                except Exception as e:
                    logger.warning(f"Failed to get video base64 for video {carousel_index}: {e}")
            
            processed_videos.append(video_result)
            if video_id:
                all_video_ids.append(video_id)
        
        # Prepare final response
        is_carousel = len(video_files) > 1
        total_credits_saved = sum(1 for v in processed_videos if v["processing"].get("ai_credits_saved", False))
        postgres_saves = sum(1 for v in processed_videos if v["database"].get("postgres_saved", False))
        qdrant_saves = sum(1 for v in processed_videos if v["database"].get("qdrant_saved", False))
        
        response = {
            "success": True,
            "message": f"{'Carousel' if is_carousel else 'Video'} processing completed successfully",
            "url": url,
            "normalized_url": normalized_url,
            "carousel_info": {
                "is_carousel": is_carousel,
                "total_videos": len(video_files),
                "processed_videos": len(processed_videos)
            },
            "processing": {
                "download": True,
                "total_videos_processed": len(processed_videos),
                "ai_credits_saved_count": total_credits_saved,
                "database_operations": {
                    "postgres_enabled": save_to_postgres,
                    "qdrant_enabled": save_to_qdrant,
                    "postgres_saves": postgres_saves,
                    "qdrant_saves": qdrant_saves
                }
            },
            "videos": processed_videos,
            "video_ids": all_video_ids
        }
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Processing failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "url": url
        }
    
    finally:
        # Cleanup temp files
        try:
            if download_result and download_result.get('temp_dir'):
                import shutil
                shutil.rmtree(download_result['temp_dir'], ignore_errors=True)
        except:
            pass

async def get_video_simple(video_id: str, include_base64: bool = False) -> Dict[str, Any]:
    """Get video data by ID from simple table."""
    try:
        db = SimpleVideoDatabase()
        await db.initialize()
        result = await db.get_video(video_id, include_base64)
        
        if result:
            return {
                "success": True,
                "video": result
            }
        else:
            return {
                "success": False,
                "error": "Video not found"
            }
            
    except Exception as e:
        logger.error(f"❌ Failed to get video: {e}")
        return {
            "success": False,
            "error": str(e)
        }

async def get_carousel_videos(url: str, include_base64: bool = False) -> Dict[str, Any]:
    """Get all videos from a carousel by URL."""
    try:
        db = SimpleVideoDatabase()
        await db.initialize()
        
        # Normalize URL
        normalized_url = normalize_url(url)
        
        # Get all videos for this URL
        db_results = await db.get_videos_by_url(normalized_url, include_base64)
        
        if db_results:
            # Convert database results to processing format
            formatted_videos = []
            for db_video in db_results:
                # Parse stored JSON data
                transcript_data = None
                scenes_data = None
                tags = []
                
                if db_video.get('transcript'):
                    try:
                        transcript_data = json.loads(db_video['transcript']) if isinstance(db_video['transcript'], str) else db_video['transcript']
                    except (json.JSONDecodeError, TypeError):
                        transcript_data = None
                
                if db_video.get('descriptions'):
                    try:
                        scenes_data = json.loads(db_video['descriptions']) if isinstance(db_video['descriptions'], str) else db_video['descriptions']
                    except (json.JSONDecodeError, TypeError):
                        scenes_data = None
                
                if db_video.get('tags'):
                    tags = db_video['tags'] if isinstance(db_video['tags'], list) else []
                
                # Format video in processing pipeline format
                formatted_video = {
                    "carousel_index": db_video.get("carousel_index", 0),
                    "video_id": db_video.get("id"),
                    "processing": {
                        "transcription": bool(transcript_data),
                        "scene_analysis": bool(scenes_data),
                        "used_existing_data": True,
                        "ai_credits_saved": True
                    },
                    "results": {
                        "transcript_data": transcript_data,
                        "scenes_data": scenes_data,
                        "tags": tags
                    },
                    "database": {
                        "saved": True,
                        "video_stored": db_video.get("has_video", False)
                    },
                    "metadata": {
                        "created_at": db_video.get("created_at"),
                        "updated_at": db_video.get("updated_at")
                    }
                }
                
                # Include base64 if requested
                if include_base64 and db_video.get("video_base64"):
                    formatted_video["results"]["video_base64"] = db_video["video_base64"]
                
                formatted_videos.append(formatted_video)
            
            return {
                "success": True,
                "url": url,
                "normalized_url": normalized_url,
                "carousel_info": {
                    "is_carousel": len(db_results) > 1,
                    "total_videos": len(db_results)
                },
                "videos": formatted_videos
            }
        else:
            return {
                "success": False,
                "error": "No videos found for this URL"
            }
            
    except Exception as e:
        logger.error(f"❌ Failed to get carousel videos: {e}")
        return {
            "success": False,
            "error": str(e)
        }

async def search_videos_simple(query: str, limit: int = 10) -> Dict[str, Any]:
    """Search videos from simple table."""
    try:
        db = SimpleVideoDatabase()
        await db.initialize()
        results = await db.search_videos(query, limit)
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to search videos: {e}")
        return {
            "success": False,
            "error": str(e)
        }

async def list_videos_simple(limit: int = 20) -> Dict[str, Any]:
    """List recent videos from simple table."""
    try:
        db = SimpleVideoDatabase()
        await db.initialize()
        results = await db.list_recent_videos(limit)
        
        return {
            "success": True,
            "videos": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to list videos: {e}")
        return {
            "success": False,
            "error": str(e)
        } 