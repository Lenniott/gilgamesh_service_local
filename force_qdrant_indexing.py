#!/usr/bin/env python3
"""
Force Qdrant Indexing and Test Search Functionality
This script will ensure vectors are properly indexed and searchable for the AI video compilation pipeline.
"""

import asyncio
import logging
from typing import List, Dict, Any
from app.db_connections import get_db_connections
from app.ai_requirements_generator import RequirementsGenerator, SearchQuery
from app.compilation_search import CompilationSearchEngine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """Main function to force indexing and test search."""
    print("🔧 QDRANT INDEXING FIX & SEARCH TEST")
    print("=" * 60)
    
    try:
        # Get database connections
        connections = await get_db_connections()
        qdrant_client = connections.get_qdrant_client()
        
        if not qdrant_client:
            print("❌ Qdrant client not available")
            return
        
        # Step 1: Check current indexing status
        await check_indexing_status(qdrant_client)
        
        # Step 2: Force indexing for both collections
        await force_indexing(qdrant_client)
        
        # Step 3: Wait for indexing to complete
        await wait_for_indexing(qdrant_client)
        
        # Step 4: Test search functionality
        await test_search_after_indexing(connections)
        
        print("\n✅ INDEXING AND SEARCH TEST COMPLETE")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise
    finally:
        await connections.close_all()

async def check_indexing_status(qdrant_client):
    """Check current indexing status of collections."""
    print("\n📊 STEP 1: CHECK INDEXING STATUS")
    print("-" * 40)
    
    collections = ["video_transcript_segments", "video_scene_descriptions"]
    
    for collection_name in collections:
        try:
            collection_info = qdrant_client.get_collection(collection_name)
            points_count = collection_info.points_count
            indexed_count = collection_info.indexed_vectors_count
            
            print(f"📁 {collection_name}:")
            print(f"   Points: {points_count}")
            print(f"   Indexed: {indexed_count}")
            print(f"   Status: {'✅ Indexed' if indexed_count > 0 else '⚠️ Not Indexed'}")
            
        except Exception as e:
            print(f"❌ Failed to check {collection_name}: {e}")

async def force_indexing(qdrant_client):
    """Force indexing for both collections."""
    print("\n🔧 STEP 2: FORCE INDEXING")
    print("-" * 40)
    
    collections = ["video_transcript_segments", "video_scene_descriptions"]
    
    for collection_name in collections:
        try:
            print(f"🚀 Forcing indexing for {collection_name}...")
            
            # Create index (this forces indexing to start)
            qdrant_client.create_payload_index(
                collection_name=collection_name,
                field_name="video_id",  # Index on video_id field
                field_schema="keyword"
            )
            
            print(f"✅ Indexing triggered for {collection_name}")
            
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"📋 Index already exists for {collection_name}")
            else:
                print(f"❌ Failed to force indexing for {collection_name}: {e}")

async def wait_for_indexing(qdrant_client):
    """Wait for indexing to complete."""
    print("\n⏳ STEP 3: WAIT FOR INDEXING")
    print("-" * 40)
    
    collections = ["video_transcript_segments", "video_scene_descriptions"]
    max_wait = 30  # seconds
    wait_interval = 2  # seconds
    
    for collection_name in collections:
        print(f"⏳ Waiting for {collection_name} indexing...")
        
        for attempt in range(max_wait // wait_interval):
            try:
                collection_info = qdrant_client.get_collection(collection_name)
                indexed_count = collection_info.indexed_vectors_count
                points_count = collection_info.points_count
                
                if indexed_count > 0:
                    print(f"✅ {collection_name} indexed: {indexed_count}/{points_count} vectors")
                    break
                else:
                    print(f"⏳ {collection_name} indexing in progress... ({attempt + 1}/{max_wait // wait_interval})")
                    await asyncio.sleep(wait_interval)
                    
            except Exception as e:
                print(f"❌ Error checking indexing status: {e}")
                break
        else:
            print(f"⚠️ {collection_name} indexing may still be in progress")

async def test_search_after_indexing(connections):
    """Test search functionality after indexing."""
    print("\n🔍 STEP 4: TEST SEARCH AFTER INDEXING")
    print("-" * 40)
    
    try:
        search_engine = CompilationSearchEngine(connections)
        
        # Test with a simple, broad query
        test_query = SearchQuery(
            query_text="exercise movement",
            priority=5,
            duration_target=30.0,
            tags_filter=[],
            exclude_terms=[],
            content_type="movement"
        )
        
        print(f"🔍 Testing search with: '{test_query.query_text}'")
        
        # Search both collections
        transcript_matches = await search_engine._search_transcript_collection(test_query, 10)
        scene_matches = await search_engine._search_scene_collection(test_query, 10)
        
        print(f"📊 RESULTS:")
        print(f"   Transcript matches: {len(transcript_matches)}")
        print(f"   Scene matches: {len(scene_matches)}")
        
        if transcript_matches:
            print(f"   📝 Best transcript match:")
            best = max(transcript_matches, key=lambda m: m.relevance_score)
            print(f"      Score: {best.relevance_score:.3f}")
            print(f"      Content: {best.content_text[:80]}...")
            print(f"      Video: {best.video_id}")
        
        if scene_matches:
            print(f"   🎬 Best scene match:")
            best = max(scene_matches, key=lambda m: m.relevance_score)
            print(f"      Score: {best.relevance_score:.3f}")
            print(f"      Content: {best.content_text[:80]}...")
            print(f"      Video: {best.video_id}")
        
        # Test with the original fitness request
        await test_fitness_search(connections)
        
        return len(transcript_matches) + len(scene_matches) > 0
        
    except Exception as e:
        print(f"❌ Search test failed: {e}")
        return False

async def test_fitness_search(connections):
    """Test with the original fitness request."""
    print(f"\n🏋️ BONUS: TEST FITNESS COMPILATION SEARCH")
    print("-" * 40)
    
    try:
        req_gen = RequirementsGenerator(connections)
        search_engine = CompilationSearchEngine(connections)
        
        # Original request
        user_context = "I haven't exercised in months, I need to rebuild my strength slowly"
        user_requirements = "10 minutes, manageable workout routines that build strength and mobility, something I can do daily"
        
        print(f"👤 Request: rebuild strength slowly, manageable workouts")
        
        # Generate search queries
        queries = await req_gen.generate_search_queries(user_context, user_requirements)
        print(f"✅ Generated {len(queries)} queries")
        
        # Test the compilation search
        compilation_result = await search_engine.search_for_compilation(
            search_queries=queries,
            max_total_duration=600.0  # 10 minutes
        )
        
        print(f"📊 COMPILATION RESULTS:")
        print(f"   Success: {compilation_result.success}")
        print(f"   Total matches: {len(compilation_result.content_matches)}")
        print(f"   Total duration: {compilation_result.total_duration:.1f}s")
        print(f"   Average relevance: {compilation_result.average_relevance:.3f}")
        print(f"   Unique videos: {compilation_result.unique_video_count}")
        
        if compilation_result.content_matches:
            print(f"   🏆 Best matches:")
            for i, match in enumerate(compilation_result.content_matches[:3], 1):
                print(f"      {i}. {match.segment_type} | Score: {match.relevance_score:.3f}")
                print(f"         Content: {match.content_text[:60]}...")
                print(f"         Duration: {match.duration:.1f}s")
        
        return compilation_result.success and len(compilation_result.content_matches) > 0
        
    except Exception as e:
        print(f"❌ Fitness search failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(main()) 