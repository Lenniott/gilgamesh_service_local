#!/usr/bin/env python3
"""
Quick test to see what content exists in the database
"""

import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_generic_searches():
    """Test with very generic terms to see what content exists."""
    
    try:
        from app.compilation_search import CompilationSearchEngine
        from app.db_connections import DatabaseConnections
        from app.ai_requirements_generator import SearchQuery
        
        # Connect to database
        connections = DatabaseConnections()
        await connections.connect_all()
        
        search_engine = CompilationSearchEngine(connections)
        
        # Test with very generic terms
        generic_terms = [
            "movement",
            "exercise", 
            "person",
            "video",
            "instruction",
            "demonstration",
            "training",
            "body",
            "action"
        ]
        
        logger.info("🔍 Testing generic search terms to see what content exists...")
        
        for term in generic_terms:
            query = SearchQuery(
                query_text=term,
                priority=5,
                duration_target=30.0,
                tags_filter=[],
                exclude_terms=[]
            )
            
            results = await search_engine.search_content_segments([query])
            total_matches = sum(len(result.matches) for result in results)
            
            logger.info(f"'{term}': {total_matches} matches")
            
            # If we find matches, show some examples
            if total_matches > 0:
                for result in results:
                    for match in result.matches[:2]:  # Show first 2 matches
                        logger.info(f"  Example: {match.content_text[:100]}...")
                break
        
        await connections.close_all()
        
    except Exception as e:
        logger.error(f"❌ Content check failed: {e}")

async def check_database_stats():
    """Check database statistics."""
    
    try:
        from app.db_connections import DatabaseConnections
        
        connections = DatabaseConnections()
        await connections.connect_all()
        
        # Check PostgreSQL stats
        async with connections.pg_pool.acquire() as conn:
            video_count = await conn.fetchval("SELECT COUNT(*) FROM simple_videos")
            video_with_base64 = await conn.fetchval("SELECT COUNT(*) FROM simple_videos WHERE video_base64 IS NOT NULL")
            
            logger.info(f"📊 PostgreSQL Stats:")
            logger.info(f"  Total videos: {video_count}")
            logger.info(f"  Videos with base64: {video_with_base64}")
        
        # Check Qdrant stats
        try:
            transcript_info = connections.qdrant_client.get_collection("video_transcript_segments")
            scene_info = connections.qdrant_client.get_collection("video_scene_descriptions")
            
            logger.info(f"📊 Qdrant Stats:")
            logger.info(f"  Transcript segments: {transcript_info.points_count}")
            logger.info(f"  Scene descriptions: {scene_info.points_count}")
            
        except Exception as e:
            logger.warning(f"⚠️ Could not get Qdrant stats: {e}")
        
        await connections.close_all()
        
    except Exception as e:
        logger.error(f"❌ Database stats check failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_database_stats())
    asyncio.run(test_generic_searches()) 