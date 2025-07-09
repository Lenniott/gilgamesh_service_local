#!/usr/bin/env python3
"""
Qdrant Collection Analysis Script
Diagnoses issues with fitness video collections and why they're not returning content.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import os
import sys
import argparse

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.db_connections import DatabaseConnections
from app.ai_requirements_generator import SearchQuery

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class CollectionInfo:
    """Information about a Qdrant collection."""
    name: str
    exists: bool
    vector_count: int
    indexed_vector_count: int
    status: str
    config: Dict[str, Any]
    sample_points: List[Dict[str, Any]]

@dataclass
class SearchTestResult:
    """Result of a search test."""
    query: str
    collection: str
    results_count: int
    best_score: float
    sample_results: List[Dict[str, Any]]
    error: Optional[str] = None

class QdrantAnalyzer:
    """Analyzes Qdrant collections for fitness video compilation."""
    
    def __init__(self):
        self.connections = None
        self.qdrant_client = None
        
        # Expected collection names
        self.expected_collections = [
            "video_transcript_segments",
            "video_scene_descriptions"
        ]
        
        # Test queries for fitness content
        self.test_queries = [
            "squat exercise form",
            "push up workout",
            "mobility stretch",
            "strength training",
            "fitness routine",
            "exercise demonstration",
            "workout movement",
            "physical training"
        ]
    
    async def initialize(self) -> bool:
        """Initialize database connections."""
        try:
            self.connections = DatabaseConnections()
            await self.connections.connect_all()
            
            self.qdrant_client = self.connections.get_qdrant_client()
            if not self.qdrant_client:
                logger.error("❌ Qdrant client not available")
                return False
            
            logger.info("✅ Qdrant analyzer initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Qdrant analyzer: {e}")
            return False
    
    async def get_collection_info(self, collection_name: str) -> CollectionInfo:
        """Get detailed information about a collection."""
        try:
            # Check if collection exists
            collections = self.qdrant_client.get_collections()
            collection_exists = any(col.name == collection_name for col in collections.collections)
            
            if not collection_exists:
                return CollectionInfo(
                    name=collection_name,
                    exists=False,
                    vector_count=0,
                    indexed_vector_count=0,
                    status="DOES_NOT_EXIST",
                    config={},
                    sample_points=[]
                )
            
            # Get collection info
            collection_info = self.qdrant_client.get_collection(collection_name)
            
            # Get collection status
            status = collection_info.status
            
            # Get vector count
            vector_count = collection_info.vectors_count if hasattr(collection_info, 'vectors_count') else 0
            
            # Get indexed vector count
            indexed_vector_count = collection_info.points_count if hasattr(collection_info, 'points_count') else vector_count
            
            # Get sample points
            sample_points = []
            try:
                # Get first 5 points as samples
                scroll_result = self.qdrant_client.scroll(
                    collection_name=collection_name,
                    limit=5,
                    with_payload=True,
                    with_vectors=False
                )
                sample_points = [
                    {
                        "id": point.id,
                        "payload": point.payload,
                        "score": getattr(point, 'score', None)
                    }
                    for point in scroll_result[0]
                ]
            except Exception as e:
                logger.warning(f"⚠️ Could not get sample points for {collection_name}: {e}")
            
            return CollectionInfo(
                name=collection_name,
                exists=True,
                vector_count=vector_count,
                indexed_vector_count=indexed_vector_count,
                status=status,
                config=collection_info.config.dict() if hasattr(collection_info.config, 'dict') else {},
                sample_points=sample_points
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to get collection info for {collection_name}: {e}")
            return CollectionInfo(
                name=collection_name,
                exists=False,
                vector_count=0,
                indexed_vector_count=0,
                status=f"ERROR: {str(e)}",
                config={},
                sample_points=[]
            )
    
    async def test_search_query(self, query: str, collection_name: str) -> SearchTestResult:
        """Test a search query on a specific collection."""
        try:
            # Generate embedding for the query
            embedding = await self.connections.generate_embedding(query)
            if not embedding:
                return SearchTestResult(
                    query=query,
                    collection=collection_name,
                    results_count=0,
                    best_score=0.0,
                    sample_results=[],
                    error="Failed to generate embedding"
                )
            
            # Search the collection
            search_result = self.qdrant_client.search(
                collection_name=collection_name,
                query_vector=embedding,
                limit=10,
                score_threshold=0.1,
                with_payload=True
            )
            
            # Process results
            sample_results = []
            best_score = 0.0
            
            for point in search_result:
                sample_results.append({
                    "id": point.id,
                    "score": point.score,
                    "payload": point.payload
                })
                best_score = max(best_score, point.score)
            
            return SearchTestResult(
                query=query,
                collection=collection_name,
                results_count=len(search_result),
                best_score=best_score,
                sample_results=sample_results
            )
            
        except Exception as e:
            return SearchTestResult(
                query=query,
                collection=collection_name,
                results_count=0,
                best_score=0.0,
                sample_results=[],
                error=str(e)
            )
    
    async def analyze_collections(self) -> Dict[str, Any]:
        """Comprehensive analysis of all collections."""
        logger.info("🔍 Starting comprehensive Qdrant collection analysis...")
        
        analysis = {
            "timestamp": asyncio.get_event_loop().time(),
            "collections": {},
            "search_tests": {},
            "issues": [],
            "recommendations": []
        }
        
        # Analyze each expected collection
        for collection_name in self.expected_collections:
            logger.info(f"📊 Analyzing collection: {collection_name}")
            collection_info = await self.get_collection_info(collection_name)
            analysis["collections"][collection_name] = collection_info.__dict__
            
            # Check for issues
            if not collection_info.exists:
                analysis["issues"].append(f"Collection '{collection_name}' does not exist")
                analysis["recommendations"].append(f"Create collection '{collection_name}'")
                continue
            
            if collection_info.vector_count == 0:
                analysis["issues"].append(f"Collection '{collection_name}' has no vectors")
                analysis["recommendations"].append(f"Add vectors to collection '{collection_name}'")
                continue
            
            if collection_info.status != "green":
                analysis["issues"].append(f"Collection '{collection_name}' status is {collection_info.status}")
                analysis["recommendations"].append(f"Check collection '{collection_name}' status")
            
            # Test search queries
            analysis["search_tests"][collection_name] = {}
            for query in self.test_queries:
                logger.info(f"🔍 Testing query '{query}' on {collection_name}")
                test_result = await self.test_search_query(query, collection_name)
                analysis["search_tests"][collection_name][query] = test_result.__dict__
                
                if test_result.error:
                    analysis["issues"].append(f"Search failed for '{query}' on {collection_name}: {test_result.error}")
                elif test_result.results_count == 0:
                    analysis["issues"].append(f"No results for '{query}' on {collection_name}")
                    analysis["recommendations"].append(f"Check vector embeddings and content in {collection_name}")
        
        # Generate summary
        total_vectors = sum(info.get("vector_count", 0) or 0 for info in analysis["collections"].values() if isinstance(info, dict))
        total_issues = len(analysis["issues"])
        
        analysis["summary"] = {
            "total_collections": len(self.expected_collections),
            "existing_collections": sum(1 for info in analysis["collections"].values() if info.get("exists", False)),
            "total_vectors": total_vectors,
            "total_issues": total_issues,
            "status": "HEALTHY" if total_issues == 0 else "ISSUES_FOUND"
        }
        
        return analysis
    
    async def check_vectorization_status(self) -> Dict[str, Any]:
        """Check the vectorization status of videos in PostgreSQL."""
        try:
            # Check if we have a PostgreSQL connection
            if not self.connections.postgres_connection:
                return {"error": "PostgreSQL connection not available"}
            
            # Query to check vectorization status
            query = """
            SELECT 
                COUNT(*) as total_videos,
                COUNT(CASE WHEN vectorized_at IS NOT NULL THEN 1 END) as vectorized_videos,
                COUNT(CASE WHEN vectorized_at IS NULL THEN 1 END) as unvectorized_videos,
                COUNT(CASE WHEN transcript IS NOT NULL THEN 1 END) as videos_with_transcript,
                COUNT(CASE WHEN descriptions IS NOT NULL THEN 1 END) as videos_with_descriptions
            FROM simple_videos
            """
            
            async with self.connections.postgres_connection.cursor() as cursor:
                await cursor.execute(query)
                result = await cursor.fetchone()
                
                return {
                    "total_videos": result[0],
                    "vectorized_videos": result[1],
                    "unvectorized_videos": result[2],
                    "videos_with_transcript": result[3],
                    "videos_with_descriptions": result[4],
                    "vectorization_percentage": (result[1] / result[0] * 100) if result[0] > 0 else 0
                }
                
        except Exception as e:
            return {"error": f"Failed to check vectorization status: {e}"}
    
    async def cleanup(self):
        """Clean up connections."""
        if self.connections:
            try:
                if hasattr(self.connections, 'cleanup'):
                    await self.connections.cleanup()
                else:
                    # Close connections manually
                    if hasattr(self.connections, 'postgres_connection') and self.connections.postgres_connection:
                        await self.connections.postgres_connection.close()
            except Exception as e:
                logger.warning(f"⚠️ Cleanup warning: {e}")

async def main():
    """Main analysis function."""
    analyzer = QdrantAnalyzer()
    
    try:
        # Initialize
        if not await analyzer.initialize():
            logger.error("❌ Failed to initialize analyzer")
            return
        
        print("\n" + "="*80)
        print("🔍 QDRANT COLLECTION ANALYSIS")
        print("="*80)
        
        # Run comprehensive analysis
        analysis = await analyzer.analyze_collections()
        
        # Check vectorization status
        vectorization_status = await analyzer.check_vectorization_status()
        analysis["vectorization_status"] = vectorization_status
        
        # Print results
        print("\n📊 COLLECTION STATUS:")
        print("-" * 40)
        
        for collection_name, info in analysis["collections"].items():
            status_icon = "✅" if info.get("exists", False) else "❌"
            print(f"{status_icon} {collection_name}:")
            if info.get("exists", False):
                print(f"   • Vectors: {info.get('vector_count', 0)}")
                print(f"   • Status: {info.get('status', 'unknown')}")
                print(f"   • Indexed: {info.get('indexed_vector_count', 0)}")
            else:
                print(f"   • Does not exist")
            print()
        
        # Print vectorization status
        print("📈 VECTORIZATION STATUS:")
        print("-" * 40)
        if "error" not in vectorization_status:
            print(f"✅ Total videos: {vectorization_status['total_videos']}")
            print(f"✅ Vectorized: {vectorization_status['vectorized_videos']}")
            print(f"❌ Unvectorized: {vectorization_status['unvectorized_videos']}")
            print(f"📝 With transcript: {vectorization_status['videos_with_transcript']}")
            print(f"🎬 With descriptions: {vectorization_status['videos_with_descriptions']}")
            print(f"📊 Vectorization: {vectorization_status['vectorization_percentage']:.1f}%")
        else:
            print(f"❌ {vectorization_status['error']}")
        print()
        
        # Print search test results
        print("🔍 SEARCH TEST RESULTS:")
        print("-" * 40)
        
        for collection_name, tests in analysis["search_tests"].items():
            print(f"\n📁 {collection_name}:")
            for query, result in tests.items():
                if result.get("error"):
                    print(f"   ❌ '{query}': {result['error']}")
                else:
                    results_count = result.get("results_count", 0)
                    best_score = result.get("best_score", 0.0)
                    status = "✅" if results_count > 0 else "❌"
                    print(f"   {status} '{query}': {results_count} results (best: {best_score:.3f})")
        
        # Print issues and recommendations
        if analysis["issues"]:
            print("\n🚨 ISSUES FOUND:")
            print("-" * 40)
            for issue in analysis["issues"]:
                print(f"❌ {issue}")
        
        if analysis["recommendations"]:
            print("\n💡 RECOMMENDATIONS:")
            print("-" * 40)
            for rec in analysis["recommendations"]:
                print(f"💡 {rec}")
        
        # Print summary
        summary = analysis["summary"]
        print(f"\n📋 SUMMARY:")
        print("-" * 40)
        print(f"Status: {summary['status']}")
        print(f"Collections: {summary['existing_collections']}/{summary['total_collections']}")
        print(f"Total vectors: {summary['total_vectors']}")
        print(f"Issues: {summary['total_issues']}")
        
        # Save detailed analysis to file
        output_file = "qdrant_analysis_results.json"
        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        print(f"\n💾 Detailed analysis saved to: {output_file}")
        
        # Sample payload analysis
        print("\n🔍 SAMPLE PAYLOAD ANALYSIS:")
        print("-" * 40)
        for collection_name, info in analysis["collections"].items():
            if info.get("exists", False) and info.get("sample_points"):
                print(f"\n📁 {collection_name} sample payloads:")
                for i, point in enumerate(info["sample_points"][:2]):  # Show first 2
                    payload = point.get("payload", {})
                    print(f"   Point {i+1}:")
                    print(f"     • video_id: {payload.get('video_id', 'N/A')}")
                    print(f"     • text/description: {payload.get('text', payload.get('description', 'N/A'))[:100]}...")
                    print(f"     • tags: {payload.get('tags', [])}")
        
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await analyzer.cleanup()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze Qdrant collections for fitness video content.")
    parser.add_argument(
        "--collections",
        nargs="*",
        help="List of Qdrant collection names to analyze (default: video_transcript_segments, video_scene_descriptions)",
    )
    args = parser.parse_args()

    # Patch QdrantAnalyzer to accept custom collections
    orig_init = QdrantAnalyzer.__init__
    def patched_init(self):
        orig_init(self)
        if args.collections:
            self.expected_collections = args.collections
    QdrantAnalyzer.__init__ = patched_init

    asyncio.run(main()) 