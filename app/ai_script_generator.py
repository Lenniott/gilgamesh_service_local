#!/usr/bin/env python3
"""
AI Script Generator for Video Compilation Pipeline
Creates structured scripts with precise timing and video assignments
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json
from app.db_connections import DatabaseConnections
from app.compilation_search import SearchResult, ContentMatch

logger = logging.getLogger(__name__)

@dataclass
class ScriptSegment:
    """Individual segment of the compilation script."""
    script_text: str
    start_time: float
    end_time: float
    assigned_video_id: str
    assigned_video_start: float
    assigned_video_end: float
    transition_type: str  # "cut", "fade", "crossfade"
    segment_type: str  # "introduction", "main_content", "transition", "conclusion"
    
    @property
    def duration(self) -> float:
        """Get segment duration in seconds."""
        return self.end_time - self.start_time
    
    @property
    def assigned_video_duration(self) -> float:
        """Get assigned video segment duration in seconds."""
        return self.assigned_video_end - self.assigned_video_start

@dataclass
class CompilationScript:
    """Complete compilation script with all segments."""
    total_duration: float
    segments: List[ScriptSegment]
    metadata: Dict[str, Any]
    
    @property
    def segment_count(self) -> int:
        """Get total number of segments."""
        return len(self.segments)
    
    @property
    def unique_videos_used(self) -> int:
        """Get number of unique videos used."""
        return len(set(segment.assigned_video_id for segment in self.segments))

class ScriptGenerator:
    """
    AI-powered script generator for video compilation.
    Creates structured scripts with precise timing and video assignments.
    """
    
    def __init__(self, connections: DatabaseConnections):
        self.connections = connections
        self.openai_client = connections.get_openai_client()
    
    async def create_segmented_script(self, 
                                    search_results: List[SearchResult],
                                    user_context: str,
                                    user_requirements: str,
                                    target_duration: float = 300.0) -> CompilationScript:
        """
        Generate script with precise timing and video assignments.
        
        Args:
            search_results: Search results from compilation search engine
            user_context: Original user context
            user_requirements: Original user requirements
            target_duration: Target duration for the compilation in seconds
            
        Returns:
            CompilationScript with all segments and assignments
        """
        if not self.openai_client:
            logger.error("❌ OpenAI client not available")
            return self._generate_fallback_script(search_results, target_duration)
        
        try:
            logger.info(f"🎬 Generating script for {len(search_results)} search results...")
            
            # Analyze available content
            content_analysis = self._analyze_available_content(search_results)
            
            # Generate script structure using OpenAI
            script_structure = await self._generate_script_structure(
                user_context, user_requirements, content_analysis, target_duration
            )
            
            # Assign video segments to script segments
            script_segments = await self._assign_video_segments(script_structure, search_results)
            
            # Optimize timing and transitions
            optimized_segments = self._optimize_timing_and_transitions(script_segments, target_duration)
            
            # Create final compilation script
            compilation_script = CompilationScript(
                total_duration=sum(segment.duration for segment in optimized_segments),
                segments=optimized_segments,
                metadata={
                    "user_context": user_context,
                    "user_requirements": user_requirements,
                    "target_duration": target_duration,
                    "content_analysis": content_analysis,
                    "generation_timestamp": self._get_timestamp(),
                    "unique_videos_used": len(set(segment.assigned_video_id for segment in optimized_segments)),
                    "total_segments": len(optimized_segments)
                }
            )
            
            logger.info(f"✅ Generated script with {len(optimized_segments)} segments, "
                       f"duration: {compilation_script.total_duration:.1f}s, "
                       f"videos used: {compilation_script.unique_videos_used}")
            
            return compilation_script
            
        except Exception as e:
            logger.error(f"❌ Script generation failed: {e}")
            return self._generate_fallback_script(search_results, target_duration)
    
    def _analyze_available_content(self, search_results: List[SearchResult]) -> Dict[str, Any]:
        """Analyze available content from search results."""
        all_matches = []
        for result in search_results:
            all_matches.extend(result.matches)
        
        if not all_matches:
            return {"total_matches": 0, "total_duration": 0.0, "content_types": {}}
        
        # Calculate total available duration
        total_duration = sum(match.duration for match in all_matches)
        
        # Analyze content types
        content_types = {}
        segment_types = {}
        
        for match in all_matches:
            # Count segment types
            segment_types[match.segment_type] = segment_types.get(match.segment_type, 0) + 1
            
            # Count content types from tags
            for tag in match.tags:
                content_types[tag] = content_types.get(tag, 0) + 1
        
        # Find most common content types
        top_content_types = sorted(content_types.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_matches": len(all_matches),
            "total_duration": total_duration,
            "average_duration": total_duration / len(all_matches),
            "segment_types": segment_types,
            "content_types": dict(top_content_types),
            "unique_videos": len(set(match.video_id for match in all_matches))
        }
    
    async def _generate_script_structure(self, user_context: str, user_requirements: str, 
                                       content_analysis: Dict[str, Any], target_duration: float) -> List[Dict[str, Any]]:
        """Generate script structure using OpenAI."""
        try:
            # Build comprehensive prompt
            prompt = self._build_script_generation_prompt(
                user_context, user_requirements, content_analysis, target_duration
            )
            
            # Call OpenAI to generate script structure
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_script_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1500,
                temperature=0.2,  # Slightly higher for creativity, but still structured
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            response_text = response.choices[0].message.content.strip()
            script_data = json.loads(response_text)
            
            return script_data.get("segments", [])
            
        except Exception as e:
            logger.error(f"❌ Script structure generation failed: {e}")
            return self._generate_fallback_script_structure(target_duration)
    
    def _get_script_system_prompt(self) -> str:
        """Get the system prompt for script generation."""
        return """You are an expert fitness video script writer and editor.

Your task is to create a structured script for a fitness video compilation that will engage viewers and provide clear, actionable guidance.

Key principles:
1. Create a logical flow from warm-up to main content to cool-down
2. Use clear, motivational language that matches the fitness level
3. Include specific timing for each segment
4. Ensure smooth transitions between different exercises
5. Make instructions clear and actionable

You must respond in valid JSON format with a segments array."""

    def _build_script_generation_prompt(self, user_context: str, user_requirements: str, 
                                      content_analysis: Dict[str, Any], target_duration: float) -> str:
        """Build the detailed prompt for script generation."""
        return f"""Create a structured script for a fitness video compilation:

CONTEXT: {user_context}
REQUIREMENTS: {user_requirements}
TARGET DURATION: {target_duration} seconds

AVAILABLE CONTENT ANALYSIS:
- Total video segments available: {content_analysis.get('total_matches', 0)}
- Available content duration: {content_analysis.get('total_duration', 0):.1f} seconds
- Content types: {', '.join(content_analysis.get('content_types', {}).keys())}
- Segment types: {content_analysis.get('segment_types', {})}

Create a script with 4-8 segments that flow logically and use the available content effectively.

Respond in this exact JSON format:
{{
  "segments": [
    {{
      "script_text": "Welcome to your morning mobility routine. Let's start with gentle movements to wake up your body.",
      "duration": 30.0,
      "segment_type": "introduction",
      "content_requirements": "welcoming introduction, gentle movements",
      "transition_type": "fade"
    }},
    {{
      "script_text": "Now we'll move into some dynamic stretches to improve your flexibility and range of motion.",
      "duration": 60.0,
      "segment_type": "main_content",
      "content_requirements": "stretching, flexibility, dynamic movement",
      "transition_type": "cut"
    }}
  ]
}}

Segment types: "introduction", "main_content", "transition", "conclusion"
Transition types: "cut", "fade", "crossfade"

Make the script engaging, clear, and appropriate for the user's fitness level. Ensure the total duration matches the target."""

    def _generate_fallback_script_structure(self, target_duration: float) -> List[Dict[str, Any]]:
        """Generate fallback script structure when OpenAI is not available."""
        logger.warning("🔄 Generating fallback script structure")
        
        # Basic 4-segment structure
        segment_duration = target_duration / 4
        
        return [
            {
                "script_text": "Welcome to your workout routine. Let's begin with some preparation movements.",
                "duration": segment_duration,
                "segment_type": "introduction",
                "content_requirements": "introduction, preparation",
                "transition_type": "fade"
            },
            {
                "script_text": "Now we'll move into the main exercises. Focus on proper form and controlled movements.",
                "duration": segment_duration,
                "segment_type": "main_content",
                "content_requirements": "main exercises, proper form",
                "transition_type": "cut"
            },
            {
                "script_text": "Let's continue with more targeted movements to build strength and improve mobility.",
                "duration": segment_duration,
                "segment_type": "main_content",
                "content_requirements": "targeted movements, strength, mobility",
                "transition_type": "cut"
            },
            {
                "script_text": "Excellent work! Let's finish with some cool-down movements to help your body recover.",
                "duration": segment_duration,
                "segment_type": "conclusion",
                "content_requirements": "cool-down, recovery",
                "transition_type": "fade"
            }
        ]
    
    async def _assign_video_segments(self, script_structure: List[Dict[str, Any]], 
                                   search_results: List[SearchResult]) -> List[ScriptSegment]:
        """Assign video segments to script segments based on content requirements."""
        script_segments = []
        current_time = 0.0
        
        # Create a pool of available matches
        available_matches = []
        for result in search_results:
            available_matches.extend(result.matches)
        
        # Sort matches by relevance score
        available_matches.sort(key=lambda m: m.relevance_score, reverse=True)
        
        for i, script_segment in enumerate(script_structure):
            # Find best matching video segment
            best_match = self._find_best_video_match(script_segment, available_matches)
            
            if best_match:
                # Calculate timing
                segment_duration = script_segment.get("duration", 30.0)
                end_time = current_time + segment_duration
                
                # Determine video segment timing
                video_start, video_end = self._calculate_video_timing(best_match, segment_duration)
                
                # Create script segment
                script_seg = ScriptSegment(
                    script_text=script_segment.get("script_text", ""),
                    start_time=current_time,
                    end_time=end_time,
                    assigned_video_id=best_match.video_id,
                    assigned_video_start=video_start,
                    assigned_video_end=video_end,
                    transition_type=script_segment.get("transition_type", "cut"),
                    segment_type=script_segment.get("segment_type", "main_content")
                )
                
                script_segments.append(script_seg)
                current_time = end_time
                
                # Remove used match from available pool (to encourage diversity)
                if best_match in available_matches:
                    available_matches.remove(best_match)
            else:
                logger.warning(f"⚠️ No video match found for script segment {i}")
        
        return script_segments
    
    def _find_best_video_match(self, script_segment: Dict[str, Any], 
                              available_matches: List[ContentMatch]) -> Optional[ContentMatch]:
        """Find the best video match for a script segment."""
        if not available_matches:
            return None
        
        content_requirements = script_segment.get("content_requirements", "").lower()
        segment_type = script_segment.get("segment_type", "main_content")
        
        # Score each match
        scored_matches = []
        for match in available_matches:
            score = 0.0
            
            # Base relevance score
            score += match.relevance_score
            
            # Content requirements matching
            if content_requirements:
                content_text_lower = match.content_text.lower()
                tags_lower = [tag.lower() for tag in match.tags]
                
                # Check if content requirements are mentioned
                for req in content_requirements.split():
                    if req in content_text_lower or any(req in tag for tag in tags_lower):
                        score += 0.1
            
            # Segment type matching
            if segment_type == "introduction" and any(tag in ["warmup", "preparation", "introduction"] for tag in match.tags):
                score += 0.15
            elif segment_type == "conclusion" and any(tag in ["cooldown", "recovery", "conclusion"] for tag in match.tags):
                score += 0.15
            elif segment_type == "main_content" and any(tag in ["exercise", "movement", "training"] for tag in match.tags):
                score += 0.1
            
            scored_matches.append((match, score))
        
        # Return the best match
        scored_matches.sort(key=lambda x: x[1], reverse=True)
        return scored_matches[0][0] if scored_matches else None
    
    def _calculate_video_timing(self, match: ContentMatch, target_duration: float) -> tuple[float, float]:
        """Calculate optimal video segment timing."""
        video_duration = match.duration
        
        if video_duration <= target_duration:
            # Use entire video segment
            return match.start_time, match.end_time
        else:
            # Use portion of video segment, preferring the beginning
            return match.start_time, match.start_time + target_duration
    
    def _optimize_timing_and_transitions(self, script_segments: List[ScriptSegment], 
                                       target_duration: float) -> List[ScriptSegment]:
        """Optimize timing and transitions for the final script."""
        if not script_segments:
            return script_segments
        
        # Calculate current total duration
        current_duration = sum(segment.duration for segment in script_segments)
        
        # Adjust timing if needed
        if abs(current_duration - target_duration) > 5.0:  # More than 5 seconds difference
            # Prevent division by zero
            if current_duration <= 0:
                logger.warning(f"⚠️ Current duration is {current_duration}, cannot scale timing")
                return script_segments
            
            scale_factor = target_duration / current_duration
            
            # Adjust each segment proportionally
            current_time = 0.0
            for segment in script_segments:
                new_duration = segment.duration * scale_factor
                segment.start_time = current_time
                segment.end_time = current_time + new_duration
                
                # Adjust video timing proportionally
                video_duration = segment.assigned_video_end - segment.assigned_video_start
                new_video_duration = video_duration * scale_factor
                segment.assigned_video_end = segment.assigned_video_start + new_video_duration
                
                current_time += new_duration
        
        # Optimize transitions
        for i, segment in enumerate(script_segments):
            if i == 0:
                # First segment should fade in
                segment.transition_type = "fade"
            elif i == len(script_segments) - 1:
                # Last segment should fade out
                segment.transition_type = "fade"
            else:
                # Middle segments can have cuts or crossfades
                if segment.segment_type == "transition":
                    segment.transition_type = "crossfade"
                else:
                    segment.transition_type = "cut"
        
        return script_segments
    
    def _generate_fallback_script(self, search_results: List[SearchResult], 
                                target_duration: float) -> CompilationScript:
        """Generate fallback script when OpenAI is not available."""
        logger.warning("🔄 Generating fallback compilation script")
        
        # Get available matches
        all_matches = []
        for result in search_results:
            all_matches.extend(result.matches)
        
        if not all_matches:
            # Create empty script
            return CompilationScript(
                total_duration=0.0,
                segments=[],
                metadata={"fallback": True, "error": "No content matches available"}
            )
        
        # Create basic segments using available matches
        segments = []
        current_time = 0.0
        
        # Prevent division by zero
        num_segments = min(4, len(all_matches))
        if num_segments == 0:
            logger.warning("⚠️ No segments available for fallback script")
            return CompilationScript(
                total_duration=0.0,
                segments=[],
                metadata={"fallback": True, "error": "No content matches available"}
            )
        
        segment_duration = target_duration / num_segments
        
        for i, match in enumerate(all_matches[:4]):  # Use up to 4 matches
            segment = ScriptSegment(
                script_text=f"Exercise segment {i+1}: {match.content_text[:100]}...",
                start_time=current_time,
                end_time=current_time + segment_duration,
                assigned_video_id=match.video_id,
                assigned_video_start=match.start_time,
                assigned_video_end=min(match.end_time, match.start_time + segment_duration),
                transition_type="cut" if i > 0 else "fade",
                segment_type="main_content"
            )
            segments.append(segment)
            current_time += segment_duration
        
        return CompilationScript(
            total_duration=current_time,
            segments=segments,
            metadata={"fallback": True, "segments_used": len(segments)}
        )
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for metadata."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def validate_script(self, script: CompilationScript) -> Dict[str, Any]:
        """
        Validate the generated script for consistency and quality.
        
        Args:
            script: CompilationScript to validate
            
        Returns:
            Dictionary with validation results
        """
        validation_results = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "statistics": {}
        }
        
        if not script.segments:
            validation_results["valid"] = False
            validation_results["errors"].append("Script has no segments")
            return validation_results
        
        # Check timing consistency
        expected_time = 0.0
        for i, segment in enumerate(script.segments):
            if abs(segment.start_time - expected_time) > 0.1:  # Allow small floating point errors
                validation_results["warnings"].append(f"Segment {i} timing gap: expected {expected_time:.1f}, got {segment.start_time:.1f}")
            
            if segment.duration <= 0:
                validation_results["errors"].append(f"Segment {i} has invalid duration: {segment.duration}")
                validation_results["valid"] = False
            
            expected_time = segment.end_time
        
        # Check video assignments
        video_ids = set()
        for i, segment in enumerate(script.segments):
            if not segment.assigned_video_id:
                validation_results["errors"].append(f"Segment {i} has no video assignment")
                validation_results["valid"] = False
            else:
                video_ids.add(segment.assigned_video_id)
            
            if segment.assigned_video_duration <= 0:
                validation_results["errors"].append(f"Segment {i} has invalid video duration: {segment.assigned_video_duration}")
                validation_results["valid"] = False
        
        # Calculate statistics
        validation_results["statistics"] = {
            "total_segments": len(script.segments),
            "total_duration": script.total_duration,
            "unique_videos": len(video_ids),
            "average_segment_duration": script.total_duration / len(script.segments),
            "transition_types": {}
        }
        
        # Count transition types
        for segment in script.segments:
            transition = segment.transition_type
            validation_results["statistics"]["transition_types"][transition] = \
                validation_results["statistics"]["transition_types"].get(transition, 0) + 1
        
        return validation_results 