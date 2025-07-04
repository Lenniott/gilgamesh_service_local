import os
import uuid
import json
import asyncio
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, HttpUrl
import logging

from app.downloaders import download_media_and_metadata
from app.transcription import transcribe_audio
from app.scene_detection import extract_scenes_with_ai_analysis
from app.db_operations import get_db_operations
from app.video_processing import cleanup_temp_files

logger = logging.getLogger(__name__)

class ProcessingOptions(BaseModel):
    """Options for video processing."""
    save: bool = False
    transcribe: Optional[str] = None  # None, "raw", or "timestamp"
    describe: bool = False
    save_to_postgres: bool = True
    save_to_qdrant: bool = True

class UnifiedVideoProcessor:
    """Unified video processor with save/transcribe/describe functionality."""
    
    def __init__(self):
        self.db_ops = None
    
    async def initialize(self):
        """Initialize database connections."""
        self.db_ops = await get_db_operations()
    
    async def process_url(self, url: str, options: ProcessingOptions) -> Dict[str, Any]:
        """
        Process a URL with specified options.
        
        Args:
            url: URL to process
            options: Processing options (save/transcribe/describe)
            
        Returns:
            Dict with results based on requested options
        """
        if not self.db_ops:
            await self.initialize()
        
        results = {
            "url": url,
            "processing_options": options.dict(),
            "results": {},
            "errors": []
        }
        
        temp_dir = None
        
        try:
            # 1. Download media and metadata
            logger.info(f"📥 Downloading media from: {url}")
            download_result = await download_media_and_metadata(url)
            temp_dir = download_result['temp_dir']
            
            # Get video files
            video_files = [f for f in download_result['files'] 
                          if f.lower().endswith(('.mp4', '.mkv', '.webm'))]
            
            if not video_files:
                results["errors"].append("No video files found in download")
                return results
            
            video_path = video_files[0]
            video_metadata = {
                "title": download_result.get('title', ''),
                "description": download_result.get('description', ''),
                "tags": download_result.get('tags', []),
                "source": download_result.get('source', 'unknown')
            }
            
            # 2. Save video functionality
            video_id = None
            if options.save:
                logger.info("💾 Saving video to database...")
                video_id = await self.db_ops.save_video_to_database(
                    video_path, url, video_metadata, options.save_to_postgres
                )
                if video_id:
                    results["results"]["video_saved"] = True
                    results["results"]["video_id"] = video_id
                else:
                    results["errors"].append("Failed to save video to database")
            
            # 3. Transcribe functionality
            transcript_results = None
            if options.transcribe:
                logger.info(f"🎤 Transcribing audio (mode: {options.transcribe})...")
                transcript_data = await asyncio.to_thread(transcribe_audio, video_path)
                
                if transcript_data:
                    # Determine chunking based on transcribe mode
                    chunk_by_timestamp = (options.transcribe == "timestamp")
                    
                    # If we don't have a video_id but need one for database storage
                    if not video_id and (options.save_to_postgres or options.save_to_qdrant):
                        # Create a temporary post/video record for transcripts
                        video_id = await self._create_minimal_video_record(url, video_metadata)
                    
                    if options.save_to_postgres or options.save_to_qdrant:
                        # Save transcription to databases
                        transcript_results = await self.db_ops.save_transcription(
                            transcript_data, video_id or str(uuid.uuid4()), url,
                            options.save_to_postgres, options.save_to_qdrant,
                            chunk_by_timestamp
                        )
                        results["results"]["transcription"] = transcript_results
                    else:
                        # Just return the transcript without saving
                        if chunk_by_timestamp:
                            results["results"]["transcript"] = transcript_data
                        else:
                            # Return as single text block
                            full_text = " ".join([seg.get('text', '') for seg in transcript_data])
                            results["results"]["transcript"] = full_text
                else:
                    results["errors"].append("Failed to transcribe audio")
            
            # 4. Describe functionality (scene detection + AI analysis)
            scene_results = None
            if options.describe:
                logger.info("🎬 Running scene detection and AI analysis...")
                
                # Create frames directory
                frames_dir = os.path.join(temp_dir, "ai_frames")
                os.makedirs(frames_dir, exist_ok=True)
                
                # Run enhanced scene detection with AI
                scenes_data = await extract_scenes_with_ai_analysis(
                    video_path, frames_dir, threshold=0.22, use_ai_analysis=True
                )
                
                if scenes_data:
                    # If we don't have a video_id but need one for database storage
                    if not video_id and (options.save_to_postgres or options.save_to_qdrant):
                        video_id = await self._create_minimal_video_record(url, video_metadata)
                    
                    if options.save_to_postgres or options.save_to_qdrant:
                        # Save scene descriptions to databases
                        scene_results = await self.db_ops.save_scene_descriptions(
                            scenes_data, video_id or str(uuid.uuid4()), url,
                            options.save_to_postgres, options.save_to_qdrant
                        )
                        results["results"]["scene_analysis"] = scene_results
                    else:
                        # Just return the scene analysis without saving
                        clean_scenes = []
                        for scene in scenes_data:
                            clean_scene = {
                                "start_time": scene.get("start_time"),
                                "end_time": scene.get("end_time"),
                                "ai_description": scene.get("ai_description"),
                                "ai_tags": scene.get("ai_tags"),
                                "analysis_success": scene.get("analysis_success")
                            }
                            clean_scenes.append(clean_scene)
                        results["results"]["scenes"] = clean_scenes
                else:
                    results["errors"].append("Failed to analyze scenes")
            
            # 5. Summary
            results["results"]["processing_complete"] = True
            if video_id:
                results["results"]["video_id"] = video_id
            
            logger.info(f"✅ Processing complete for {url}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Processing failed for {url}: {e}")
            results["errors"].append(f"Processing failed: {str(e)}")
            return results
            
        finally:
            # Clean up temporary files
            if temp_dir and os.path.exists(temp_dir):
                try:
                    await asyncio.to_thread(cleanup_temp_files, temp_dir)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp files: {e}")
    
    async def _create_minimal_video_record(self, url: str, metadata: Dict[str, Any]) -> Optional[str]:
        """Create minimal video record for transcripts/scenes without full video saving."""
        try:
            async with self.db_ops.connections.get_pg_connection_context() as conn:
                async with conn.transaction():
                    # Insert post
                    post_id = await self.db_ops._insert_or_get_post(conn, url, metadata)
                    
                    # Insert minimal video record
                    video_query = """
                    INSERT INTO gilgamesh_sm_videos (
                        id, post_id, transcript, created_at
                    ) VALUES (
                        gen_random_uuid(), $1::uuid, $2, CURRENT_TIMESTAMP
                    )
                    RETURNING id;
                    """
                    
                    video_id = await conn.fetchval(
                        video_query,
                        post_id,
                        json.dumps({"type": "metadata_only", "original_url": url})  # Store URL in transcript field as metadata
                    )
                    
                    return str(video_id)
                    
        except Exception as e:
            logger.error(f"Failed to create minimal video record: {e}")
            return None

# Global processor instance
unified_processor = UnifiedVideoProcessor()

async def process_url_unified(url: str, options: ProcessingOptions) -> Dict[str, Any]:
    """
    Unified URL processing function.
    
    Args:
        url: URL to process
        options: Processing options
        
    Returns:
        Dict with processing results
    """
    return await unified_processor.process_url(url, options)

# --- EXAMPLE USAGE ---

async def example_usage():
    """Example usage of the unified processor."""
    
    # Example 1: Just transcribe (return transcript without saving)
    options1 = ProcessingOptions(
        transcribe="timestamp",
        save_to_postgres=False,
        save_to_qdrant=False
    )
    
    # Example 2: Full processing with database storage
    options2 = ProcessingOptions(
        save=True,
        transcribe="timestamp", 
        describe=True,
        save_to_postgres=True,
        save_to_qdrant=True
    )
    
    # Example 3: AI analysis only, save to Qdrant but not PostgreSQL
    options3 = ProcessingOptions(
        describe=True,
        save_to_postgres=False,
        save_to_qdrant=True
    )
    
    # Example 4: Save video base64 only
    options4 = ProcessingOptions(
        save=True,
        save_to_postgres=True,
        save_to_qdrant=False
    )
    
    test_url = "https://www.youtube.com/shorts/2hvRmabCWS4"
    
    print("🧪 Example 1: Transcribe only (no saving)")
    result1 = await process_url_unified(test_url, options1)
    print(f"Result: {result1}")
    
if __name__ == "__main__":
    asyncio.run(example_usage()) 