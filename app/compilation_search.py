#!/usr/bin/env python3
"""
Enhanced Vector Search Engine for Video Compilation Pipeline
Leverages existing Qdrant infrastructure for content discovery and segment matching
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from app.db_connections import DatabaseConnections
from app.ai_requirements_generator import SearchQuery

logger = logging.getLogger(__name__)

@dataclass
class ContentMatch:
    """Represents a matched video segment from vector search."""
    video_id: str
    segment_type: str  # "transcript" or "scene"
    start_time: float
    end_time: float
    relevance_score: float
    content_text: str
    tags: List[str]
    metadata: Dict[str, Any]
    
    @property
    def duration(self) -> float:
        """Get segment duration in seconds."""
        return self.end_time - self.start_time

@dataclass
class SearchResult:
    """Aggregated search results for a query."""
    query: SearchQuery
    matches: List[ContentMatch]
    total_matches: int
    search_time: float
    
    @property
    def best_match(self) -> Optional[ContentMatch]:
        """Get the highest scoring match."""
        return max(self.matches, key=lambda m: m.relevance_score) if self.matches else None

class CompilationSearchEngine:
    """
    Enhanced vector search engine for video compilation.
    Uses existing Qdrant collections: video_transcript_segments, video_scene_descriptions
    """
    
    def __init__(self, connections: DatabaseConnections):
        self.connections = connections
        self.qdrant_client = connections.get_qdrant_client()
        self.openai_client = connections.get_openai_client()
        
        # Collection names from existing system
        self.transcript_collection = "video_transcript_segments"
        self.scene_collection = "video_scene_descriptions"
    
    async def search_content_segments(self, queries: List[SearchQuery], 
                                    max_results_per_query: int = 10) -> List[SearchResult]:
        """
        Search existing vector database for relevant content segments.
        
        Args:
            queries: List of SearchQuery objects from requirements generator
            max_results_per_query: Maximum results to return per query
            
        Returns:
            List of SearchResult objects with matched content
        """
        if not self.qdrant_client:
            logger.error("❌ Qdrant client not available")
            return []
        
        if not self.openai_client:
            logger.error("❌ OpenAI client not available for embeddings")
            return []
        
        search_results = []
        
        for query in queries:
            logger.info(f"🔍 Searching for: {query.query_text[:50]}...")
            
            try:
                import time
                start_time = time.time()
                
                # Search both transcript and scene collections
                transcript_matches = await self._search_transcript_collection(query, max_results_per_query // 2)
                scene_matches = await self._search_scene_collection(query, max_results_per_query // 2)
                
                # Combine and rank results
                all_matches = transcript_matches + scene_matches
                
                # Filter and rank matches
                filtered_matches = self._filter_and_rank_matches(all_matches, query)
                
                # Limit results
                final_matches = filtered_matches[:max_results_per_query]
                
                search_time = time.time() - start_time
                
                search_result = SearchResult(
                    query=query,
                    matches=final_matches,
                    total_matches=len(all_matches),
                    search_time=search_time
                )
                
                search_results.append(search_result)
                
                logger.info(f"✅ Found {len(final_matches)} matches for query (search time: {search_time:.2f}s)")
                
            except Exception as e:
                logger.error(f"❌ Search failed for query '{query.query_text}': {e}")
                # Add empty result to maintain query order
                search_results.append(SearchResult(
                    query=query,
                    matches=[],
                    total_matches=0,
                    search_time=0.0
                ))
        
        return search_results
    
    async def _search_transcript_collection(self, query: SearchQuery, limit: int) -> List[ContentMatch]:
        """Search the transcript segments collection."""
        try:
            # Generate embedding for the query
            embedding = await self.connections.generate_embedding(query.query_text)
            if not embedding:
                logger.warning(f"⚠️ Failed to generate embedding for query: {query.query_text}")
                return []
            
            # Search Qdrant collection
            search_result = self.qdrant_client.search(
                collection_name=self.transcript_collection,
                query_vector=embedding,
                limit=limit,
                score_threshold=0.1,  # Much lower threshold for more permissive matching
                with_payload=True
            )
            
            matches = []
            for point in search_result:
                try:
                    payload = point.payload
                    
                    # Extract metadata from payload (handle both field name formats)
                    video_id = payload.get("video_id", "")
                    start_time = float(payload.get("start", payload.get("start_time", 0)))
                    end_time = float(payload.get("end", payload.get("end_time", 0)))
                    content_text = payload.get("text", "")
                    tags = payload.get("tags", [])
                    
                    # Create ContentMatch
                    match = ContentMatch(
                        video_id=video_id,
                        segment_type="transcript",
                        start_time=start_time,
                        end_time=end_time,
                        relevance_score=point.score,
                        content_text=content_text,
                        tags=tags,
                        metadata=payload
                    )
                    
                    matches.append(match)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to parse transcript search result: {e}")
                    continue
            
            return matches
            
        except Exception as e:
            logger.error(f"❌ Transcript collection search failed: {e}")
            return []
    
    async def _search_scene_collection(self, query: SearchQuery, limit: int) -> List[ContentMatch]:
        """Search the scene descriptions collection."""
        try:
            # Generate embedding for the query
            embedding = await self.connections.generate_embedding(query.query_text)
            if not embedding:
                logger.warning(f"⚠️ Failed to generate embedding for query: {query.query_text}")
                return []
            
            # Search Qdrant collection
            search_result = self.qdrant_client.search(
                collection_name=self.scene_collection,
                query_vector=embedding,
                limit=limit,
                score_threshold=0.1,  # Much lower threshold for more permissive matching
                with_payload=True
            )
            
            matches = []
            for point in search_result:
                try:
                    payload = point.payload
                    
                    # Extract metadata from payload (handle both field name formats)
                    video_id = payload.get("video_id", "")
                    start_time = float(payload.get("start_time", payload.get("start", 0)))
                    end_time = float(payload.get("end_time", payload.get("end", 0)))
                    content_text = payload.get("description", "")
                    tags = payload.get("tags", [])
                    
                    # Create ContentMatch
                    match = ContentMatch(
                        video_id=video_id,
                        segment_type="scene",
                        start_time=start_time,
                        end_time=end_time,
                        relevance_score=point.score,
                        content_text=content_text,
                        tags=tags,
                        metadata=payload
                    )
                    
                    matches.append(match)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to parse scene search result: {e}")
                    continue
            
            return matches
            
        except Exception as e:
            logger.error(f"❌ Scene collection search failed: {e}")
            return []
    
    def _filter_and_rank_matches(self, matches: List[ContentMatch], query: SearchQuery) -> List[ContentMatch]:
        """Filter and rank matches based on query criteria."""
        filtered_matches = []
        
        for match in matches:
            # Filter by duration (if specified)
            if query.duration_target > 0:
                duration_diff = abs(match.duration - query.duration_target)
                # Allow up to 50% deviation from target duration
                max_deviation = query.duration_target * 0.5
                if duration_diff > max_deviation:
                    continue
            
            # Filter by required tags (if any tags exist)
            if query.tags_filter and match.tags:  # Only filter if both exist
                match_tags_lower = [tag.lower() for tag in match.tags]
                required_tags_lower = [tag.lower() for tag in query.tags_filter]
                
                # Check if at least one required tag is present
                if not any(req_tag in match_tags_lower for req_tag in required_tags_lower):
                    # Add small penalty instead of filtering out
                    match.relevance_score *= 0.8
            
            # Filter by exclude terms (with penalty instead of hard filter)
            if query.exclude_terms:
                content_lower = match.content_text.lower()
                tags_lower = [tag.lower() for tag in match.tags]
                
                # Apply penalty if exclude terms are found
                if any(term.lower() in content_lower for term in query.exclude_terms):
                    match.relevance_score *= 0.5
                if any(term.lower() in tags_lower for term in query.exclude_terms):
                    match.relevance_score *= 0.5
            
            # Calculate enhanced relevance score
            enhanced_score = self._calculate_enhanced_score(match, query)
            match.relevance_score = enhanced_score
            
            filtered_matches.append(match)
        
        # Sort by enhanced relevance score (highest first)
        filtered_matches.sort(key=lambda m: m.relevance_score, reverse=True)
        
        return filtered_matches
    
    def _calculate_enhanced_score(self, match: ContentMatch, query: SearchQuery) -> float:
        """Calculate enhanced relevance score based on multiple factors."""
        base_score = match.relevance_score
        
        # Duration matching bonus
        duration_bonus = 0.0
        if query.duration_target > 0:
            duration_diff = abs(match.duration - query.duration_target)
            max_deviation = query.duration_target * 0.5
            duration_bonus = max(0, (max_deviation - duration_diff) / max_deviation) * 0.1
        
        # Tag matching bonus
        tag_bonus = 0.0
        if query.tags_filter:
            match_tags_lower = [tag.lower() for tag in match.tags]
            required_tags_lower = [tag.lower() for tag in query.tags_filter]
            
            matching_tags = sum(1 for req_tag in required_tags_lower if req_tag in match_tags_lower)
            tag_bonus = (matching_tags / len(query.tags_filter)) * 0.15
        
        # Content type bonus
        content_type_bonus = 0.0
        if query.content_type == "instruction" and match.segment_type == "transcript":
            content_type_bonus = 0.05
        elif query.content_type == "movement" and match.segment_type == "scene":
            content_type_bonus = 0.05
        
        # Priority weighting
        priority_weight = query.priority / 10.0
        
        # Calculate final score
        enhanced_score = (base_score + duration_bonus + tag_bonus + content_type_bonus) * priority_weight
        
        return enhanced_score
    
    async def get_content_diversity(self, search_results: List[SearchResult]) -> Dict[str, Any]:
        """
        Analyze content diversity across search results.
        
        Args:
            search_results: List of SearchResult objects
            
        Returns:
            Dictionary with diversity metrics
        """
        all_matches = []
        for result in search_results:
            all_matches.extend(result.matches)
        
        if not all_matches:
            return {"total_matches": 0, "unique_videos": 0, "diversity_score": 0.0}
        
        # Count unique videos
        unique_videos = set(match.video_id for match in all_matches)
        
        # Count segment types
        segment_types = {}
        for match in all_matches:
            segment_types[match.segment_type] = segment_types.get(match.segment_type, 0) + 1
        
        # Count content types (from tags)
        content_types = {}
        for match in all_matches:
            for tag in match.tags:
                content_types[tag] = content_types.get(tag, 0) + 1
        
        # Calculate diversity score (0-1, higher is more diverse)
        diversity_score = min(1.0, len(unique_videos) / max(1, len(all_matches)))
        
        return {
            "total_matches": len(all_matches),
            "unique_videos": len(unique_videos),
            "segment_types": segment_types,
            "content_types": content_types,
            "diversity_score": diversity_score,
            "average_relevance": sum(m.relevance_score for m in all_matches) / len(all_matches)
        }
    
    async def optimize_search_results(self, search_results: List[SearchResult], 
                                    target_duration: float = 300.0,
                                    max_videos_per_query: int = 3) -> List[SearchResult]:
        """
        Optimize search results for better video compilation.
        
        Args:
            search_results: List of SearchResult objects
            target_duration: Target total duration for compilation
            max_videos_per_query: Maximum videos to use per query
            
        Returns:
            Optimized list of SearchResult objects
        """
        optimized_results = []
        
        for result in search_results:
            if not result.matches:
                optimized_results.append(result)
                continue
            
            # Group matches by video_id
            video_groups = {}
            for match in result.matches:
                if match.video_id not in video_groups:
                    video_groups[match.video_id] = []
                video_groups[match.video_id].append(match)
            
            # Select best matches from each video
            optimized_matches = []
            for video_id, matches in video_groups.items():
                # Sort by relevance score
                matches.sort(key=lambda m: m.relevance_score, reverse=True)
                
                # Take the best match from this video
                optimized_matches.append(matches[0])
                
                # Stop if we have enough videos
                if len(optimized_matches) >= max_videos_per_query:
                    break
            
            # Sort final matches by relevance
            optimized_matches.sort(key=lambda m: m.relevance_score, reverse=True)
            
            # Create optimized result
            optimized_result = SearchResult(
                query=result.query,
                matches=optimized_matches,
                total_matches=result.total_matches,
                search_time=result.search_time
            )
            
            optimized_results.append(optimized_result)
        
        return optimized_results
    
    def get_search_summary(self, search_results: List[SearchResult]) -> Dict[str, Any]:
        """
        Generate a summary of search results for debugging and logging.
        
        Args:
            search_results: List of SearchResult objects
            
        Returns:
            Dictionary with search summary statistics
        """
        if not search_results:
            return {"total_queries": 0, "total_matches": 0, "total_search_time": 0.0}
        
        total_matches = sum(len(result.matches) for result in search_results)
        total_search_time = sum(result.search_time for result in search_results)
        
        # Find best and worst performing queries
        best_query = max(search_results, key=lambda r: len(r.matches))
        worst_query = min(search_results, key=lambda r: len(r.matches))
        
        # Calculate average relevance scores
        all_matches = []
        for result in search_results:
            all_matches.extend(result.matches)
        
        avg_relevance = sum(m.relevance_score for m in all_matches) / len(all_matches) if all_matches else 0.0
        
        return {
            "total_queries": len(search_results),
            "total_matches": total_matches,
            "total_search_time": total_search_time,
            "average_matches_per_query": total_matches / len(search_results),
            "average_search_time": total_search_time / len(search_results),
            "average_relevance_score": avg_relevance,
            "best_query": {
                "text": best_query.query.query_text,
                "matches": len(best_query.matches)
            },
            "worst_query": {
                "text": worst_query.query.query_text,
                "matches": len(worst_query.matches)
            },
            "queries_with_no_matches": sum(1 for r in search_results if not r.matches)
        }

    # --- ENHANCED COMPILATION SEARCH METHOD ---

    async def search_for_compilation(self, search_queries: List[SearchQuery], 
                                   max_total_duration: float = 600.0,
                                   max_results_per_query: int = 10) -> 'CompilationSearchResult':
        """
        High-level search method for video compilation.
        
        Args:
            search_queries: List of SearchQuery objects
            max_total_duration: Maximum total duration for all matches
            max_results_per_query: Maximum results to return per query
            
        Returns:
            CompilationSearchResult with aggregated results
        """
        try:
            # Perform the actual search
            search_results = await self.search_content_segments(
                queries=search_queries,
                max_results_per_query=max_results_per_query
            )
            
            # Aggregate all matches
            all_matches = []
            for result in search_results:
                all_matches.extend(result.matches)
            
            # Sort by relevance score
            all_matches.sort(key=lambda m: m.relevance_score, reverse=True)
            
            # Filter by total duration
            selected_matches = []
            total_duration = 0.0
            
            for match in all_matches:
                if total_duration + match.duration <= max_total_duration:
                    selected_matches.append(match)
                    total_duration += match.duration
                else:
                    break
            
            # Calculate average relevance
            avg_relevance = sum(m.relevance_score for m in selected_matches) / len(selected_matches) if selected_matches else 0.0
            
            # Generate search summary
            search_summary = self.get_search_summary(search_results)
            
            return CompilationSearchResult(
                success=True,
                content_matches=selected_matches,
                total_duration=total_duration,
                average_relevance=avg_relevance,
                search_summary=search_summary
            )
            
        except Exception as e:
            logger.error(f"❌ Compilation search failed: {e}")
            return CompilationSearchResult(
                success=False,
                content_matches=[],
                total_duration=0.0,
                average_relevance=0.0,
                search_summary={},
                error_message=str(e)
            )


# --- COMPILATION SEARCH RESULT ---

@dataclass
class CompilationSearchResult:
    """High-level search result for video compilation requests."""
    success: bool
    content_matches: List[ContentMatch]
    total_duration: float
    average_relevance: float
    search_summary: Dict[str, Any]
    error_message: Optional[str] = None
    
    @property
    def unique_video_count(self) -> int:
        """Get count of unique videos in results."""
        return len(set(match.video_id for match in self.content_matches)) 