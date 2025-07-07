#!/usr/bin/env python3
"""
AI Requirements Generator for Video Compilation Pipeline
Transforms user context and requirements into structured search queries for vector retrieval
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from app.db_connections import DatabaseConnections

logger = logging.getLogger(__name__)

@dataclass
class SearchQuery:
    """Structured search query for video content discovery."""
    query_text: str
    priority: int  # 1-10 (10 = highest priority)
    duration_target: float  # Target duration in seconds
    tags_filter: List[str]  # Required tags
    exclude_terms: List[str]  # Terms to exclude
    content_type: str  # "movement", "instruction", "demonstration", "transition"

class RequirementsGenerator:
    """
    Transform user context and requirements into structured search queries.
    Uses OpenAI to break down high-level requirements into specific, searchable chunks.
    """
    
    def __init__(self, connections: DatabaseConnections):
        self.connections = connections
        self.openai_client = connections.get_openai_client() if connections else None
    
    async def generate_search_queries(self, user_context: str, user_requirements: str) -> List[SearchQuery]:
        """
        Transform user requirements into vectorizable search chunks.
        
        Args:
            user_context: High-level context (e.g., "I'm creating a morning workout routine")
            user_requirements: Specific requirements (e.g., "5 minutes, beginner-friendly, mobility focus")
            
        Returns:
            List of SearchQuery objects optimized for vector search
        """
        if not self.openai_client:
            logger.error("❌ OpenAI client not available")
            return self._generate_fallback_queries(user_context, user_requirements)
        
        try:
            # Create comprehensive prompt for query generation
            prompt = self._build_query_generation_prompt(user_context, user_requirements)
            
            # Call OpenAI to generate structured queries
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1000,
                temperature=0.1,  # Low temperature for consistent, structured output
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            response_text = response.choices[0].message.content.strip()
            queries_data = self._parse_openai_response(response_text)
            
            # Convert to SearchQuery objects
            search_queries = []
            for query_data in queries_data:
                search_query = SearchQuery(
                    query_text=query_data.get("query_text", ""),
                    priority=query_data.get("priority", 5),
                    duration_target=query_data.get("duration_target", 30.0),
                    tags_filter=query_data.get("tags_filter", []),
                    exclude_terms=query_data.get("exclude_terms", []),
                    content_type=query_data.get("content_type", "movement")
                )
                search_queries.append(search_query)
            
            logger.info(f"✅ Generated {len(search_queries)} search queries from user requirements")
            return search_queries
            
        except Exception as e:
            logger.error(f"❌ Failed to generate search queries: {e}")
            return self._generate_fallback_queries(user_context, user_requirements)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for query generation."""
        return """You are an expert fitness trainer specializing in creating personalized workout routines.

Your task is to analyze the user's workout request and break it down into specific exercises and movements that would create an effective routine.

For example, if someone asks for a "full body mobility routine", you should think:
1. What areas need mobility work? (hips, shoulders, spine, ankles)
2. What basic exercises target these areas? (hip flexor stretches, shoulder circles)
3. How to progress through the routine? (start with basic movements, build complexity)
4. What specific movements would work best? (downward dog for posterior chain, cat-cow for spine)

Then create 5-8 specific search queries that will find video demonstrations of these movements.

Key principles:
1. Think like a trainer - what exercises would YOU choose for this person?
2. Be specific about movements - "hip flexor stretch with forward lunge" vs just "stretch"
3. Consider the user's level and goals
4. Include proper form cues and alignment details
5. Mix different types of movements (mobility, strength, balance)

You must respond in valid JSON format with an array of query objects."""

    def _build_query_generation_prompt(self, user_context: str, user_requirements: str) -> str:
        """Build the detailed prompt for query generation."""
        return f"""As an expert fitness trainer, analyze this workout request and create a sequence of specific exercises:

CONTEXT: {user_context}
REQUIREMENTS: {user_requirements}

First, think about what exercises and movements would create an effective routine. Consider:
- What muscle groups and movement patterns are needed?
- What specific exercises would work best for the user's level?
- How should the movements progress?
- What form cues and alignment details matter?

Then generate 5-8 search queries to find video demonstrations of these movements.

Respond in this exact JSON format:
{{
  "queries": [
    {{
      "query_text": "detailed description of the exercise with form cues",
      "priority": 8,
      "duration_target": 30.0,
      "tags_filter": ["movement_type", "body_part"],
      "exclude_terms": ["advanced", "equipment"],
      "content_type": "movement"
    }}
  ]
}}

Example query texts:
- "Hip flexor stretch in lunge position, front knee aligned over ankle"
- "Basic squat with feet shoulder width, emphasis on knee tracking"
- "Cat-cow spinal mobility flow with breath coordination"
- "Shoulder mobility circles and blade retraction"

Content types: "movement", "instruction", "demonstration", "transition"
Priority: 1-10 (10 = most important)
Duration target: 10-60 seconds per query

Focus on finding clear demonstrations that match the user's level and goals."""

    def _parse_openai_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse OpenAI JSON response into query data."""
        try:
            import json
            data = json.loads(response_text)
            return data.get("queries", [])
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse OpenAI response: {e}")
            logger.error(f"Raw response: {response_text}")
            return []
    
    def _generate_fallback_queries(self, user_context: str, user_requirements: str) -> List[SearchQuery]:
        """Generate fallback queries when OpenAI is not available."""
        logger.warning("🔄 Generating fallback search queries")
        
        # Extract key terms from requirements
        requirements_lower = user_requirements.lower()
        
        # Basic query patterns based on common fitness terms
        fallback_queries = []
        
        # Workout type queries
        if "workout" in requirements_lower or "exercise" in requirements_lower:
            fallback_queries.append(SearchQuery(
                query_text="basic workout exercise movement",
                priority=8,
                duration_target=30.0,
                tags_filter=["exercise", "movement"],
                exclude_terms=["advanced", "equipment"],
                content_type="movement"
            ))
        
        # Mobility/flexibility queries
        if "mobility" in requirements_lower or "stretch" in requirements_lower:
            fallback_queries.append(SearchQuery(
                query_text="mobility stretching flexibility movement",
                priority=9,
                duration_target=45.0,
                tags_filter=["mobility", "flexibility"],
                exclude_terms=["strength", "cardio"],
                content_type="movement"
            ))
        
        # Strength queries
        if "strength" in requirements_lower or "muscle" in requirements_lower:
            fallback_queries.append(SearchQuery(
                query_text="strength training muscle building",
                priority=8,
                duration_target=30.0,
                tags_filter=["strength", "muscle"],
                exclude_terms=["cardio", "flexibility"],
                content_type="movement"
            ))
        
        # Core queries
        if "core" in requirements_lower or "abs" in requirements_lower:
            fallback_queries.append(SearchQuery(
                query_text="core abdominal strengthening exercise",
                priority=7,
                duration_target=30.0,
                tags_filter=["core", "abs"],
                exclude_terms=["legs", "arms"],
                content_type="movement"
            ))
        
        # Beginner-friendly queries
        if "beginner" in requirements_lower:
            fallback_queries.append(SearchQuery(
                query_text="beginner friendly basic exercise",
                priority=9,
                duration_target=40.0,
                tags_filter=["beginner", "basic"],
                exclude_terms=["advanced", "complex"],
                content_type="instruction"
            ))
        
        # Add generic movement query if no specific matches
        if not fallback_queries:
            fallback_queries.append(SearchQuery(
                query_text="exercise movement fitness training",
                priority=6,
                duration_target=30.0,
                tags_filter=["exercise", "movement"],
                exclude_terms=[],
                content_type="movement"
            ))
        
        # Add instruction/demonstration queries
        fallback_queries.append(SearchQuery(
            query_text="how to perform exercise instruction",
            priority=7,
            duration_target=25.0,
            tags_filter=["instruction", "demonstration"],
            exclude_terms=["advanced"],
            content_type="instruction"
        ))
        
        # Add transition/warm-up queries
        fallback_queries.append(SearchQuery(
            query_text="warm up preparation movement",
            priority=6,
            duration_target=20.0,
            tags_filter=["warmup", "preparation"],
            exclude_terms=["intense", "advanced"],
            content_type="transition"
        ))
        
        logger.info(f"✅ Generated {len(fallback_queries)} fallback search queries")
        return fallback_queries

    async def validate_queries(self, queries: List[SearchQuery]) -> List[SearchQuery]:
        """
        Validate and optimize search queries.
        
        Args:
            queries: List of SearchQuery objects to validate
            
        Returns:
            List of validated and optimized SearchQuery objects
        """
        validated_queries = []
        
        for query in queries:
            # Basic validation
            if not query.query_text or len(query.query_text.strip()) < 5:
                logger.warning(f"⚠️ Skipping invalid query: {query.query_text}")
                continue
            
            # Ensure priority is within bounds
            query.priority = max(1, min(10, query.priority))
            
            # Ensure duration target is reasonable
            query.duration_target = max(10.0, min(120.0, query.duration_target))
            
            # Clean up tags and exclude terms
            query.tags_filter = [tag.strip().lower() for tag in query.tags_filter if tag.strip()]
            query.exclude_terms = [term.strip().lower() for term in query.exclude_terms if term.strip()]
            
            # Validate content type
            valid_content_types = ["movement", "instruction", "demonstration", "transition"]
            if query.content_type not in valid_content_types:
                query.content_type = "movement"
            
            validated_queries.append(query)
        
        # Sort by priority (highest first)
        validated_queries.sort(key=lambda q: q.priority, reverse=True)
        
        logger.info(f"✅ Validated {len(validated_queries)} search queries")
        return validated_queries

    def get_query_summary(self, queries: List[SearchQuery]) -> Dict[str, Any]:
        """
        Generate a summary of the search queries for debugging and logging.
        
        Args:
            queries: List of SearchQuery objects
            
        Returns:
            Dictionary with query summary statistics
        """
        if not queries:
            return {"total_queries": 0, "total_duration": 0.0}
        
        total_duration = sum(q.duration_target for q in queries)
        content_types = {}
        priority_distribution = {}
        
        for query in queries:
            # Count content types
            content_types[query.content_type] = content_types.get(query.content_type, 0) + 1
            
            # Count priority distribution
            priority_range = f"{query.priority}-{query.priority}"
            if query.priority <= 3:
                priority_range = "Low (1-3)"
            elif query.priority <= 6:
                priority_range = "Medium (4-6)"
            elif query.priority <= 8:
                priority_range = "High (7-8)"
            else:
                priority_range = "Critical (9-10)"
            
            priority_distribution[priority_range] = priority_distribution.get(priority_range, 0) + 1
        
        return {
            "total_queries": len(queries),
            "total_duration_target": total_duration,
            "average_duration": total_duration / len(queries),
            "content_types": content_types,
            "priority_distribution": priority_distribution,
            "highest_priority": max(q.priority for q in queries),
            "lowest_priority": min(q.priority for q in queries)
        } 