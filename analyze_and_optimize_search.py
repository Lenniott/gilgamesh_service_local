#!/usr/bin/env python3
"""
Analyze Qdrant Content and Optimize Search Queries
This script examines the actual content in Qdrant and creates search queries that match available content.
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
    """Main function to analyze content and optimize search."""
    print("🔍 CONTENT ANALYSIS & SEARCH OPTIMIZATION")
    print("=" * 60)
    
    try:
        # Get database connections
        connections = await get_db_connections()
        qdrant_client = connections.get_qdrant_client()
        
        if not qdrant_client:
            print("❌ Qdrant client not available")
            return
        
        # Step 1: Analyze actual content in collections
        content_analysis = await analyze_qdrant_content(qdrant_client)
        
        # Step 2: Create optimized search queries based on actual content
        optimized_queries = create_optimized_queries(content_analysis)
        
        # Step 3: Test optimized search
        await test_optimized_search(connections, optimized_queries)
        
        # Step 4: Test full compilation pipeline with optimized queries
        await test_compilation_with_optimized_queries(connections, optimized_queries)
        
        print("\n✅ CONTENT ANALYSIS & OPTIMIZATION COMPLETE")
        
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        raise
    finally:
        await connections.close_all()

async def analyze_qdrant_content(qdrant_client):
    """Analyze actual content in Qdrant collections."""
    print("\n📊 STEP 1: ANALYZE ACTUAL CONTENT")
    print("-" * 40)
    
    content_analysis = {
        "transcript_keywords": {},
        "scene_keywords": {},
        "common_terms": [],
        "exercise_types": [],
        "sample_content": []
    }
    
    collections = ["video_transcript_segments", "video_scene_descriptions"]
    
    for collection_name in collections:
        print(f"\n📁 Analyzing {collection_name}...")
        
        try:
            # Get sample of content
            search_result = qdrant_client.scroll(
                collection_name=collection_name,
                limit=20,  # Get more samples
                with_payload=True,
                with_vectors=False
            )
            
            points, _ = search_result
            print(f"   📋 Analyzing {len(points)} content samples...")
            
            # Extract and analyze content
            for i, point in enumerate(points):
                payload = point.payload
                
                # Get text content
                if collection_name == "video_transcript_segments":
                    content_text = payload.get('text', '')
                    content_type = "transcript"
                else:
                    content_text = payload.get('description', '')
                    content_type = "scene"
                
                if content_text:
                    # Store sample content
                    content_analysis["sample_content"].append({
                        "type": content_type,
                        "text": content_text,
                        "video_id": payload.get('video_id', ''),
                        "tags": payload.get('tags', [])
                    })
                    
                    # Extract keywords
                    keywords = extract_keywords_from_text(content_text)
                    
                    if content_type == "transcript":
                        for keyword in keywords:
                            content_analysis["transcript_keywords"][keyword] = \
                                content_analysis["transcript_keywords"].get(keyword, 0) + 1
                    else:
                        for keyword in keywords:
                            content_analysis["scene_keywords"][keyword] = \
                                content_analysis["scene_keywords"].get(keyword, 0) + 1
                    
                    # Show sample content
                    if i < 5:  # Show first 5 samples
                        print(f"      {i+1}. {content_text[:80]}...")
                        if payload.get('tags'):
                            print(f"         Tags: {payload.get('tags', [])}")
                
        except Exception as e:
            print(f"❌ Failed to analyze {collection_name}: {e}")
    
    # Find common terms across both collections
    transcript_words = set(content_analysis["transcript_keywords"].keys())
    scene_words = set(content_analysis["scene_keywords"].keys())
    common_words = transcript_words & scene_words
    
    # Sort by frequency
    transcript_top = sorted(content_analysis["transcript_keywords"].items(), 
                           key=lambda x: x[1], reverse=True)[:10]
    scene_top = sorted(content_analysis["scene_keywords"].items(), 
                      key=lambda x: x[1], reverse=True)[:10]
    
    print(f"\n📈 CONTENT ANALYSIS RESULTS:")
    print(f"   Total samples analyzed: {len(content_analysis['sample_content'])}")
    print(f"   Top transcript terms: {[term for term, count in transcript_top[:5]]}")
    print(f"   Top scene terms: {[term for term, count in scene_top[:5]]}")
    print(f"   Common terms: {list(common_words)[:10]}")
    
    content_analysis["common_terms"] = list(common_words)
    content_analysis["top_transcript_terms"] = [term for term, count in transcript_top]
    content_analysis["top_scene_terms"] = [term for term, count in scene_top]
    
    return content_analysis

def extract_keywords_from_text(text: str) -> List[str]:
    """Extract meaningful keywords from text content."""
    import re
    
    # Convert to lowercase and extract words
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Filter out common stop words
    stop_words = {
        'the', 'and', 'are', 'for', 'with', 'this', 'that', 'you', 'your', 
        'they', 'them', 'have', 'has', 'had', 'will', 'was', 'were', 'been',
        'being', 'from', 'into', 'through', 'during', 'before', 'after',
        'above', 'below', 'here', 'there', 'when', 'where', 'why', 'how'
    }
    
    # Focus on fitness-related and action words
    fitness_keywords = []
    for word in words:
        if word not in stop_words and len(word) >= 3:
            fitness_keywords.append(word)
    
    return fitness_keywords

def create_optimized_queries(content_analysis: Dict[str, Any]) -> List[SearchQuery]:
    """Create search queries based on actual content analysis."""
    print(f"\n🎯 STEP 2: CREATE OPTIMIZED QUERIES")
    print("-" * 40)
    
    optimized_queries = []
    
    # Get top terms from actual content
    top_terms = content_analysis["top_transcript_terms"][:5] + content_analysis["top_scene_terms"][:5]
    common_terms = content_analysis["common_terms"][:5]
    
    print(f"📝 Creating queries based on actual content terms...")
    print(f"   Top content terms: {top_terms[:10]}")
    print(f"   Common terms: {common_terms}")
    
    # Create broad queries using actual content terms
    query_templates = [
        ("exercise movement", ["exercise", "movement"], 8),
        ("core training", ["core", "training"], 8),
        ("strength workout", ["strength", "workout"], 7),
        ("body movement", ["body", "movement"], 7),
        ("muscle training", ["muscle", "training"], 6),
    ]
    
    # Add queries based on actual content terms
    for term in top_terms[:5]:
        if term and len(term) >= 4:  # Only meaningful terms
            query_templates.append((f"{term} exercise", [term], 6))
    
    for i, (query_text, tags, priority) in enumerate(query_templates):
        optimized_query = SearchQuery(
            query_text=query_text,
            priority=priority,
            duration_target=30.0,
            tags_filter=tags,
            exclude_terms=[],  # Remove exclusions that might be too restrictive
            content_type="movement"
        )
        optimized_queries.append(optimized_query)
        
        print(f"   {i+1}. '{query_text}' (Priority: {priority})")
    
    return optimized_queries

async def test_optimized_search(connections, optimized_queries: List[SearchQuery]):
    """Test the optimized search queries."""
    print(f"\n🔍 STEP 3: TEST OPTIMIZED SEARCH")
    print("-" * 40)
    
    search_engine = CompilationSearchEngine(connections)
    
    print(f"🔍 Testing {len(optimized_queries)} optimized queries...")
    
    total_matches = 0
    successful_queries = 0
    
    for i, query in enumerate(optimized_queries[:5], 1):  # Test first 5
        print(f"\n   Query {i}: '{query.query_text}'")
        
        try:
            # Test individual collection searches
            transcript_matches = await search_engine._search_transcript_collection(query, 5)
            scene_matches = await search_engine._search_scene_collection(query, 5)
            
            query_total = len(transcript_matches) + len(scene_matches)
            total_matches += query_total
            
            if query_total > 0:
                successful_queries += 1
            
            print(f"      Transcript: {len(transcript_matches)} | Scene: {len(scene_matches)} | Total: {query_total}")
            
            # Show best match
            all_matches = transcript_matches + scene_matches
            if all_matches:
                best = max(all_matches, key=lambda m: m.relevance_score)
                print(f"      Best: {best.relevance_score:.3f} | {best.segment_type}")
                print(f"      Content: {best.content_text[:60]}...")
                
        except Exception as e:
            print(f"      ❌ Search failed: {e}")
    
    print(f"\n📊 OPTIMIZED SEARCH RESULTS:")
    print(f"   Total matches: {total_matches}")
    print(f"   Successful queries: {successful_queries}/{min(5, len(optimized_queries))}")
    print(f"   Success rate: {(successful_queries/min(5, len(optimized_queries))*100):.1f}%")
    
    return successful_queries > 0

async def test_compilation_with_optimized_queries(connections, optimized_queries: List[SearchQuery]):
    """Test full compilation search with optimized queries."""
    print(f"\n🎬 STEP 4: TEST COMPILATION WITH OPTIMIZED QUERIES")
    print("-" * 40)
    
    try:
        search_engine = CompilationSearchEngine(connections)
        
        print(f"🎯 Testing compilation search with content-based queries...")
        
        # Use optimized queries for compilation search
        compilation_result = await search_engine.search_for_compilation(
            search_queries=optimized_queries,
            max_total_duration=600.0  # 10 minutes
        )
        
        print(f"📊 COMPILATION RESULTS:")
        print(f"   Success: {compilation_result.success}")
        print(f"   Total matches: {len(compilation_result.content_matches)}")
        print(f"   Total duration: {compilation_result.total_duration:.1f}s")
        print(f"   Average relevance: {compilation_result.average_relevance:.3f}")
        print(f"   Unique videos: {compilation_result.unique_video_count}")
        
        if compilation_result.content_matches:
            print(f"   🏆 Best matches for compilation:")
            for i, match in enumerate(compilation_result.content_matches[:5], 1):
                print(f"      {i}. {match.segment_type} | Score: {match.relevance_score:.3f}")
                print(f"         Content: {match.content_text[:60]}...")
                print(f"         Duration: {match.duration:.1f}s | Video: {match.video_id[:8]}...")
        else:
            print(f"   ⚠️ No matches found for compilation")
        
        # Show what a successful compilation request would look like
        if compilation_result.content_matches:
            print(f"\n🎉 SUCCESS! Video compilation is now possible:")
            print(f"   - Found {len(compilation_result.content_matches)} usable segments")
            print(f"   - Total duration: {compilation_result.total_duration:.1f} seconds")
            print(f"   - From {compilation_result.unique_video_count} different videos")
            print(f"   - Average relevance: {compilation_result.average_relevance:.3f}")
        
        return compilation_result.success and len(compilation_result.content_matches) > 0
        
    except Exception as e:
        print(f"❌ Compilation test failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(main()) 