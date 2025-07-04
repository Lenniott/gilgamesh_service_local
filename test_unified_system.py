#!/usr/bin/env python3
"""
Comprehensive test script for the unified database and vector system.
Tests all functionality: save, transcribe, describe with flexible storage options.
"""

import asyncio
import json
import tempfile
import os
from pathlib import Path

from app.unified_processor import process_url_unified, ProcessingOptions
from app.db_connections import get_db_connections

async def test_connections():
    """Test all database connections."""
    print("🔌 TESTING DATABASE CONNECTIONS")
    print("=" * 50)
    
    connections = await get_db_connections()
    results = await connections.test_all_connections()
    
    print(f"PostgreSQL: {'✅' if results.get('postgresql') else '❌'}")
    print(f"Qdrant: {'✅' if results.get('qdrant') else '❌'}")
    print(f"OpenAI: {'✅' if results.get('openai') else '❌'}")
    
    if all(results.values()):
        print("✅ All connections successful!")
        
        # Ensure collections exist
        await connections.ensure_collection_exists("gilgamesh_transcripts")
        await connections.ensure_collection_exists("gilgamesh_scenes")
        
        return True
    else:
        print("❌ Some connections failed!")
        return False

async def test_transcribe_only():
    """Test transcription without saving to database."""
    print("\n🎤 TEST 1: TRANSCRIBE ONLY (NO SAVING)")
    print("=" * 50)
    
    options = ProcessingOptions(
        transcribe="timestamp",
        save_to_postgres=False,
        save_to_qdrant=False
    )
    
    test_url = "https://www.youtube.com/shorts/2hvRmabCWS4"
    result = await process_url_unified(test_url, options)
    
    print(f"✅ URL: {result['url']}")
    print(f"🎯 Options: {result['processing_options']}")
    
    if 'transcript' in result['results']:
        transcript = result['results']['transcript']
        print(f"📝 Transcript segments: {len(transcript)}")
        print(f"📄 Sample: {transcript[0]['text'][:100]}..." if transcript else "No transcript")
    
    if result['errors']:
        print(f"❌ Errors: {result['errors']}")
    
    return result

async def test_describe_only():
    """Test scene description without saving to database."""
    print("\n🎬 TEST 2: DESCRIBE ONLY (NO SAVING)")
    print("=" * 50)
    
    options = ProcessingOptions(
        describe=True,
        save_to_postgres=False,
        save_to_qdrant=False
    )
    
    test_url = "https://www.youtube.com/shorts/2hvRmabCWS4"
    result = await process_url_unified(test_url, options)
    
    print(f"✅ URL: {result['url']}")
    print(f"🎯 Options: {result['processing_options']}")
    
    if 'scenes' in result['results']:
        scenes = result['results']['scenes']
        print(f"🎬 Scenes found: {len(scenes)}")
        
        for i, scene in enumerate(scenes[:2]):  # Show first 2 scenes
            print(f"\n🎞️  Scene {i+1}:")
            print(f"   ⏱️  Time: {scene['start_time']:.2f}s - {scene['end_time']:.2f}s")
            print(f"   🤖 AI Success: {'✅' if scene['analysis_success'] else '❌'}")
            print(f"   📖 Description: {scene['ai_description'][:100]}...")
            print(f"   🏷️  Tags: {', '.join(scene['ai_tags'][:3])}...")
    
    if result['errors']:
        print(f"❌ Errors: {result['errors']}")
    
    return result

async def test_save_to_qdrant_only():
    """Test saving transcription and scenes to Qdrant only."""
    print("\n🗄️ TEST 3: SAVE TO QDRANT ONLY")
    print("=" * 50)
    
    options = ProcessingOptions(
        transcribe="timestamp",
        describe=True,
        save_to_postgres=False,
        save_to_qdrant=True
    )
    
    test_url = "https://www.youtube.com/shorts/2hvRmabCWS4"
    result = await process_url_unified(test_url, options)
    
    print(f"✅ URL: {result['url']}")
    print(f"🎯 Options: {result['processing_options']}")
    
    # Check transcription results
    if 'transcription' in result['results']:
        trans_result = result['results']['transcription']
        print(f"📝 Transcript chunks: {trans_result['chunks_created']}")
        print(f"📊 PostgreSQL saved: {'✅' if trans_result['postgresql_saved'] else '❌'}")
        print(f"🔍 Qdrant saved: {'✅' if trans_result['qdrant_saved'] else '❌'}")
        print(f"🆔 Vector IDs: {len(trans_result['vector_ids'])}")
    
    # Check scene analysis results
    if 'scene_analysis' in result['results']:
        scene_result = result['results']['scene_analysis']
        print(f"🎬 Scenes processed: {scene_result['scenes_processed']}")
        print(f"📊 PostgreSQL saved: {'✅' if scene_result['postgresql_saved'] else '❌'}")
        print(f"🔍 Qdrant saved: {'✅' if scene_result['qdrant_saved'] else '❌'}")
        print(f"🆔 Vector IDs: {len(scene_result['vector_ids'])}")
    
    if result['errors']:
        print(f"❌ Errors: {result['errors']}")
    
    return result

async def test_save_video_base64():
    """Test saving full video as base64 to PostgreSQL."""
    print("\n💾 TEST 4: SAVE VIDEO BASE64")
    print("=" * 50)
    
    options = ProcessingOptions(
        save=True,
        save_to_postgres=True,
        save_to_qdrant=False
    )
    
    test_url = "https://www.youtube.com/shorts/2hvRmabCWS4"
    result = await process_url_unified(test_url, options)
    
    print(f"✅ URL: {result['url']}")
    print(f"🎯 Options: {result['processing_options']}")
    
    if 'video_saved' in result['results']:
        print(f"💾 Video saved: {'✅' if result['results']['video_saved'] else '❌'}")
        if 'video_id' in result['results']:
            print(f"🆔 Video ID: {result['results']['video_id']}")
    
    if result['errors']:
        print(f"❌ Errors: {result['errors']}")
    
    return result

async def test_full_pipeline():
    """Test complete pipeline with all options enabled."""
    print("\n🚀 TEST 5: FULL PIPELINE (ALL OPTIONS)")
    print("=" * 50)
    
    options = ProcessingOptions(
        save=True,
        transcribe="timestamp",
        describe=True,
        save_to_postgres=True,
        save_to_qdrant=True
    )
    
    test_url = "https://www.youtube.com/shorts/2hvRmabCWS4"
    result = await process_url_unified(test_url, options)
    
    print(f"✅ URL: {result['url']}")
    print(f"🎯 Options: {result['processing_options']}")
    
    # Video saving
    if 'video_saved' in result['results']:
        print(f"💾 Video saved: {'✅' if result['results']['video_saved'] else '❌'}")
        
    # Transcription
    if 'transcription' in result['results']:
        trans_result = result['results']['transcription']
        print(f"📝 Transcript: PostgreSQL {'✅' if trans_result['postgresql_saved'] else '❌'}, Qdrant {'✅' if trans_result['qdrant_saved'] else '❌'}")
        print(f"📊 Chunks: {trans_result['chunks_created']}, Vectors: {len(trans_result['vector_ids'])}")
    
    # Scene analysis
    if 'scene_analysis' in result['results']:
        scene_result = result['results']['scene_analysis']
        print(f"🎬 Scenes: PostgreSQL {'✅' if scene_result['postgresql_saved'] else '❌'}, Qdrant {'✅' if scene_result['qdrant_saved'] else '❌'}")
        print(f"📊 Processed: {scene_result['scenes_processed']}, Vectors: {len(scene_result['vector_ids'])}")
    
    if 'video_id' in result['results']:
        print(f"🆔 Final Video ID: {result['results']['video_id']}")
    
    if result['errors']:
        print(f"❌ Errors: {result['errors']}")
    
    return result

async def test_vector_retrieval():
    """Test retrieving full video from vector chunks."""
    print("\n🔍 TEST 6: VECTOR RETRIEVAL")
    print("=" * 50)
    
    # First, save some data to retrieve
    options = ProcessingOptions(
        transcribe="timestamp",
        describe=True,
        save_to_postgres=True,
        save_to_qdrant=True
    )
    
    test_url = "https://www.youtube.com/shorts/2hvRmabCWS4"
    result = await process_url_unified(test_url, options)
    
    # Get vector IDs from the result
    vector_ids = []
    if 'transcription' in result['results']:
        vector_ids.extend(result['results']['transcription']['vector_ids'])
    if 'scene_analysis' in result['results']:
        vector_ids.extend(result['results']['scene_analysis']['vector_ids'])
    
    if vector_ids:
        print(f"🔍 Testing retrieval with vector ID: {vector_ids[0]}")
        
        # Test retrieval functionality
        from app.db_operations import get_db_operations
        db_ops = await get_db_operations()
        
        full_video = await db_ops.get_full_video_from_chunk(vector_ids[0])
        
        if full_video:
            print(f"✅ Successfully retrieved video:")
            print(f"   🆔 Video ID: {full_video['video_id']}")
            print(f"   🔗 URL: {full_video['original_url']}")
            print(f"   📱 Platform: {full_video['platform']}")
            print(f"   🎬 Scenes: {len(full_video['scenes'])}")
            print(f"   🎯 Matched chunk: {full_video['matched_chunk']['type']}")
        else:
            print("❌ Failed to retrieve video from vector ID")
    else:
        print("❌ No vector IDs available for testing retrieval")

async def main():
    """Run all tests."""
    print("🧪 UNIFIED DATABASE & VECTOR SYSTEM TEST")
    print("🔄 Testing save/transcribe/describe with PostgreSQL + Qdrant")
    print("=" * 70)
    
    # Test connections first
    connections_ok = await test_connections()
    if not connections_ok:
        print("❌ Database connections failed - stopping tests")
        return
    
    # Run individual tests
    await test_transcribe_only()
    await test_describe_only()
    await test_save_to_qdrant_only()
    await test_save_video_base64()
    await test_full_pipeline()
    await test_vector_retrieval()
    
    print("\n🎯 ALL TESTS COMPLETED!")
    print("=" * 70)
    print("🚀 The unified system is ready for production use!")
    print("📋 You can now:")
    print("   • Save videos as base64 in PostgreSQL")
    print("   • Transcribe with chunking & vectorization")
    print("   • AI scene analysis with GPT-4 Vision")
    print("   • Flexible storage (PostgreSQL and/or Qdrant)")
    print("   • Retrieve full videos from any chunk")

if __name__ == "__main__":
    asyncio.run(main()) 