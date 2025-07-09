#!/usr/bin/env python3
"""
AI Script Generator for Video Compilation Pipeline
Generates structured JSON with script segments, video clips, and audio.
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import base64
import tempfile
import os

# Import existing components
from app.db_connections import DatabaseConnections
from app.compilation_search import ContentMatch
from app.audio_generator import OpenAITTSGenerator
from app.video_processing import extract_and_downscale_scene
from app.simple_db_operations import SimpleVideoDatabase

logger = logging.getLogger(__name__)

@dataclass
class VideoClip:
    """Individual video clip with base64 data."""
    video_id: str
    start: float
    end: float
    video: Optional[str] = None  # base64 video clip (square or 9:16)

@dataclass
class CompilationSegment:
    """Single segment of the compilation."""
    script_segment: str           # AI-generated instructional text
    clips: List[VideoClip]       # 1-3 clips per segment
    audio: Optional[str] = None  # base64 audio for this segment
    duration: float = 0.0        # Audio duration (clips loop to match)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format matching vision doc."""
        return {
            "script_segment": self.script_segment,
            "clips": [
                {
                    "video_id": clip.video_id,
                    "start": clip.start,
                    "end": clip.end,
                    "video": clip.video
                } for clip in self.clips
            ],
            "audio": self.audio,
            "duration": self.duration
        }

class AIScriptGenerator:
    """
    AI Script Generator for video compilation pipeline.
    Generates complete compilation JSON with script segments, video clips, and audio.
    """
    
    def __init__(self, connections: DatabaseConnections):
        self.connections = connections
        self.audio_generator = OpenAITTSGenerator(connections)
        self.video_db = SimpleVideoDatabase()
        
    async def initialize(self):
        """Initialize the script generator."""
        try:
            await self.video_db.initialize()
            logger.info("✅ AI Script Generator initialized")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize AI Script Generator: {e}")
            return False
    
    async def collect_content_context(self, content_matches: List[ContentMatch]) -> Dict[str, Any]:
        """
        Collect and organize all available content context.
            
        Returns:
        {
            "video_segments": [
                {
                    "video_id": "video_123",
                    "start_time": 15.0,
                    "end_time": 25.0,
                    "scene_description": "Person doing squats with proper form",
                    "transcript": "Alright, let's do some squats. Keep your feet shoulder width apart...",
                    "tags": ["squat", "strength", "lower_body"]
                }
            ],
            "available_exercises": ["squat", "pushup", "plank"],
            "total_duration": 180.0
        }
        """
        try:
            video_segments = []
            available_exercises = set()
            total_duration = 0.0
        
        # Group matches by video_id and timestamp
        grouped_matches = {}
        for match in content_matches:
            key = (match.video_id, match.start_time, match.end_time)
            if key not in grouped_matches:
                grouped_matches[key] = {"scene": None, "transcript": None}
            grouped_matches[key][match.segment_type] = match
        
        # Process each group
        for (video_id, start_time, end_time), matches in grouped_matches.items():
            scene_match = matches["scene"]
            transcript_match = matches["transcript"]
            
            if not scene_match:
                continue
            
                # Extract exercise name from scene description
                scene_text = scene_match.content_text.lower()
                exercise_keywords = ["squat", "push", "pull", "plank", "lunge", "jump", "stretch", "mobility", "strength"]
                found_exercises = [ex for ex in exercise_keywords if ex in scene_text]
                available_exercises.update(found_exercises)
                
                segment = {
                    "video_id": video_id,
                    "start_time": start_time,
                    "end_time": end_time,
                    "scene_description": scene_match.content_text,
                    "transcript": transcript_match.content_text if transcript_match else "",
                    "tags": scene_match.tags or []
                }
                
                video_segments.append(segment)
                total_duration += (end_time - start_time)
            
            return {
                "video_segments": video_segments,
                "available_exercises": list(available_exercises),
                "total_duration": total_duration
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to collect content context: {e}")
            return {
                "video_segments": [],
                "available_exercises": [],
                "total_duration": 0.0
            }

    async def generate_workout_requirements(self, user_input: str) -> Dict[str, Any]:
        """
        Generate structured workout requirements from user input.
        
        This creates a detailed specification of what the workout needs to achieve,
        which will then guide video selection and exercise planning.
        """
        try:
            prompt = f"""
You are a fitness programming expert. Create detailed workout requirements for the following user input:

USER INPUT: {user_input}

Generate a JSON object with this structure:
{{
    "workout_type": "string (e.g., 'strength', 'mobility', 'skill')",
    "target_duration": "number in minutes",
    "primary_goals": ["array of main objectives"],
    "movement_patterns": ["array of required movement patterns"],
    "muscle_groups": ["array of target muscle groups"],
    "skill_requirements": ["array of specific skills to develop"],
    "equipment_constraints": ["array of available equipment"],
    "intensity_level": "string (beginner/intermediate/advanced)",
    "progression_focus": ["array of progression areas"],
    "time_distribution": {{
        "warmup_percentage": "number",
        "main_work_percentage": "number", 
        "cooldown_percentage": "number"
    }},
    "exercise_categories": [
        {{
            "category": "string (e.g., 'activation', 'strength', 'skill')",
            "time_allocation": "number in seconds",
            "movement_requirements": ["array of specific movement needs"],
            "intensity_notes": "string"
        }}
    ],
    "success_criteria": ["array of measurable outcomes"],
    "safety_considerations": ["array of safety requirements"]
}}

Focus on:
- What the exercises need to demonstrate/achieve
- Movement patterns and skill development
- Time management and progression
- Safety and scalability
- Realistic workout structure

Return only valid JSON.
"""
            
            response = await self.connections.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a fitness programming expert. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            requirements_text = response.choices[0].message.content.strip()
            requirements = json.loads(requirements_text)
            
            logger.info(f"✅ Generated workout requirements with {len(requirements.get('exercise_categories', []))} categories")
            return requirements
            
        except Exception as e:
            logger.error(f"❌ Failed to generate workout requirements: {e}")
            # Return fallback requirements
            return {
                "workout_type": "general",
                "target_duration": 10,
                "primary_goals": ["general fitness"],
                "movement_patterns": ["push", "pull", "squat"],
                "muscle_groups": ["full body"],
                "skill_requirements": ["basic movement"],
                "equipment_constraints": ["bodyweight only"],
                "intensity_level": "beginner",
                "progression_focus": ["form"],
                "time_distribution": {
                    "warmup_percentage": 20,
                    "main_work_percentage": 70,
                    "cooldown_percentage": 10
                },
                "exercise_categories": [
                    {
                        "category": "activation",
                        "time_allocation": 120,
                        "movement_requirements": ["mobility", "activation"],
                        "intensity_notes": "light"
                    },
                    {
                        "category": "strength",
                        "time_allocation": 420,
                        "movement_requirements": ["push", "pull", "core"],
                        "intensity_notes": "moderate"
                    },
                    {
                        "category": "cooldown",
                        "time_allocation": 60,
                        "movement_requirements": ["mobility", "stretching"],
                        "intensity_notes": "light"
                    }
                ],
                "success_criteria": ["complete workout"],
                "safety_considerations": ["proper form"]
            }

    async def generate_structured_compilation_script_with_requirements(self, 
                                                                   content_matches: List[ContentMatch],
                                                                   workout_requirements: Dict[str, Any],
                                                                   user_requirements: str) -> Dict[str, Any]:
        """
        Generate a complete structured script using workout requirements for better planning.
        
        Returns structured object with:
        {
            "segments": [
                {
                    "exercise_name": "Squat",
                    "reps": "10",
                    "rounds": "1",
                    "form_cues": "feet shoulder width",
                    "target_video_id": "video_123",
                    "start_time": 15.0,
                    "end_time": 25.0,
                    "category": "strength",
                    "text_overlay": "Squat - 10 reps",
                    "loop_video": true
                }
            ],
            "total_rounds": 3,
            "workout_structure": "warmup -> strength -> cooldown"
        }
        """
        try:
            # Collect content context
            content_context = await self.collect_content_context(content_matches)
            
            # Create content summary for AI
            video_summaries = []
            for segment in content_context["video_segments"][:15]:  # Increased limit for better selection
                summary = f"- {segment['scene_description'][:100]}... (tags: {', '.join(segment['tags'])})"
                video_summaries.append(summary)
            
            content_summary = "\n".join(video_summaries)
            
            # Extract workout requirements for AI
            workout_type = workout_requirements.get("workout_type", "general")
            target_duration = workout_requirements.get("target_duration", 10)
            primary_goals = workout_requirements.get("primary_goals", [])
            exercise_categories = workout_requirements.get("exercise_categories", [])
            
            # Generate AI prompt for structured script using requirements
            prompt = f"""
You are a fitness video script writer. Create a structured workout plan based on detailed requirements.

WORKOUT REQUIREMENTS:
- Type: {workout_type}
- Target Duration: {target_duration} minutes
- Primary Goals: {', '.join(primary_goals)}
- Exercise Categories: {exercise_categories}

USER REQUIREMENTS: {user_requirements}

AVAILABLE CONTENT:
{content_summary}

AVAILABLE EXERCISES: {', '.join(content_context['available_exercises'])}

Generate a JSON object with this structure:
{{
    "segments": [
        {{
            "exercise_name": "Exercise Name",
            "reps": "number or time",
            "rounds": "1",
            "form_cues": "specific form instructions",
            "target_video_id": "video_123",
            "start_time": 15.0,
            "end_time": 25.0,
            "category": "strength/activation/skill/cooldown",
            "text_overlay": "Exercise Name - X reps",
            "loop_video": true/false,
            "duration": 30.0
        }}
    ],
    "total_rounds": 1,
    "workout_structure": "category1 -> category2 -> category3"
}}

Rules:
- Create a COMPLETE workout that matches the workout requirements
- Use 6-10 exercises for a full workout (not just 3)
- Distribute time according to exercise categories
- Add text overlays for each exercise
- Loop videos if they're shorter than the segment duration
- Match exercises to available video content
- Ensure diversity across video sources
- Use available exercises: {', '.join(content_context['available_exercises'])}
- Return valid JSON only
"""
            
            # Call OpenAI to generate structured script
            response = await self.connections.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a fitness video script writer. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,  # Increased for more complex workouts
                temperature=0.2,  # Lower temperature for more consistent JSON
                response_format={"type": "json_object"}
            )
            
            # Parse the response with error handling
            script_text = response.choices[0].message.content.strip()
            try:
                structured_script = json.loads(script_text)
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON parsing error: {e}")
                logger.error(f"Raw response: {script_text[:500]}...")
                # Try to fix common JSON issues
                try:
                    # Remove any trailing commas or fix common issues
                    script_text = script_text.replace(',]', ']').replace(',}', '}')
                    structured_script = json.loads(script_text)
                except:
                    # Return fallback structured script
                    logger.warning("🔄 Using fallback structured script due to JSON parsing error")
                    return {
                        "segments": [
                            {
                                "exercise_name": "Basic Movement",
                                "reps": "10",
                                "rounds": "1",
                                "form_cues": "proper form",
                                "target_video_id": content_matches[0].video_id if content_matches else "",
                                "start_time": 0.0,
                                "end_time": 30.0,
                                "category": "strength",
                                "text_overlay": "Basic Movement - 10 reps",
                                "loop_video": True,
                                "duration": 30.0
                            }
                        ],
                        "total_rounds": 1,
                        "workout_structure": "simple workout"
                    }
            
            logger.info(f"✅ Generated structured script with {len(structured_script.get('segments', []))} segments")
            return structured_script
            
        except Exception as e:
            logger.error(f"❌ Failed to generate structured compilation script with requirements: {e}")
            # Return fallback structured script
            return {
                "segments": [
                    {
                        "exercise_name": "Basic Movement",
                        "reps": "10",
                        "rounds": "1",
                        "form_cues": "proper form",
                        "target_video_id": content_matches[0].video_id if content_matches else "",
                        "start_time": 0.0,
                        "end_time": 30.0,
                        "category": "strength",
                        "text_overlay": "Basic Movement - 10 reps",
                        "loop_video": True,
                        "duration": 30.0
                    }
                ],
                "total_rounds": 1,
                "workout_structure": "simple workout"
            }

    async def generate_structured_compilation_script(self, 
                                                   content_matches: List[ContentMatch],
                                                   user_requirements: str) -> Dict[str, Any]:
        """
        Generate a complete structured script for the entire compilation.
        
        Returns structured object with:
        {
            "segments": [
                {
                    "exercise_name": "Squat",
                    "reps": "10",
                    "rounds": "1",
                    "form_cues": "feet shoulder width",
                    "target_video_id": "video_123",
                    "start_time": 15.0,
                    "end_time": 25.0
                }
            ],
            "total_rounds": 3,
            "workout_structure": "warmup -> strength -> cooldown"
        }
        """
        try:
            # Collect content context
            content_context = await self.collect_content_context(content_matches)
            
            # Create content summary for AI
            video_summaries = []
            for segment in content_context["video_segments"][:10]:  # Limit to first 10
                summary = f"- {segment['scene_description'][:100]}... (tags: {', '.join(segment['tags'])})"
                video_summaries.append(summary)
            
            content_summary = "\n".join(video_summaries)
            
            # Generate AI prompt for structured script
            prompt = f"""
You are a fitness video script writer. Create a structured workout plan.

USER REQUIREMENTS: {user_requirements}

AVAILABLE CONTENT:
{content_summary}

AVAILABLE EXERCISES: {', '.join(content_context['available_exercises'])}

Generate a JSON object with this structure:
{{
    "segments": [
        {{
            "exercise_name": "Squat",
            "reps": "10",
            "rounds": "1", 
            "form_cues": "feet shoulder width",
            "target_video_id": "video_123",
            "start_time": 15.0,
            "end_time": 25.0
        }}
    ],
    "total_rounds": 3,
    "workout_structure": "warmup -> strength -> cooldown"
}}

Rules:
- Use ONLY exercise name, reps, and rounds
- No narrative fluff
- Match exercises to available video content
- Ensure diversity across video sources
- Keep segments 10-30 seconds each
- Use available exercises: {', '.join(content_context['available_exercises'])}
- Return valid JSON only
"""
            
            # Call OpenAI to generate structured script
            response = await self.connections.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Use cheaper model for cost reduction
                messages=[
                    {"role": "system", "content": "You are a fitness video script writer. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,  # Reduced from 1000 for cost savings
                temperature=0.3,  # Lower temperature for more consistent output
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            script_text = response.choices[0].message.content.strip()
            structured_script = json.loads(script_text)
            
            logger.info(f"✅ Generated structured script with {len(structured_script.get('segments', []))} segments")
            return structured_script
            
        except Exception as e:
            logger.error(f"❌ Failed to generate structured compilation script: {e}")
            # Return fallback structured script
            return {
                "segments": [
                    {
                        "exercise_name": "Basic Movement",
                        "reps": "10",
                        "rounds": "1",
                        "form_cues": "proper form",
                        "target_video_id": content_matches[0].video_id if content_matches else "",
                        "start_time": 0.0,
                        "end_time": 30.0
                    }
                ],
                "total_rounds": 1,
                "workout_structure": "simple workout"
            }

    async def parse_structured_script_to_segments(self, 
                                                structured_script: Dict[str, Any],
                                                content_matches: List[ContentMatch]) -> List[Dict[str, Any]]:
        """
        Parse the structured script into the existing segment format.
        
        Converts structured exercise data into the existing compilation JSON format.
        Enforces diversity by selecting from different videos for each segment.
        """
        try:
            segments = []
            used_video_ids = set()  # Track used videos for diversity
            
            for i, segment_data in enumerate(structured_script.get("segments", [])):
                exercise_name = segment_data.get("exercise_name", "Exercise")
                reps = segment_data.get("reps", "10")
                rounds = segment_data.get("rounds", "1")
                form_cues = segment_data.get("form_cues", "")
                
                # Create simple script text
                script_text = f"{exercise_name} {reps} reps"
                if form_cues:
                    script_text += f" {form_cues}"
                
                # Find matching video content with diversity enforcement
                target_video_id = segment_data.get("target_video_id", "")
                matching_content = None
                
                if target_video_id:
                    # Try to find exact match
                    for match in content_matches:
                        if match.video_id == target_video_id:
                            matching_content = match
                            used_video_ids.add(match.video_id)
                            break
                
                # If no exact match or for diversity, select from unused videos
                if not matching_content and content_matches:
                    # Find best available content that hasn't been used yet
                    available_matches = [m for m in content_matches if m.video_id not in used_video_ids]
                    
                    if available_matches:
                        # Select the first available match
                        matching_content = available_matches[0]
                        used_video_ids.add(matching_content.video_id)
                    else:
                        # If all videos used, reset and use first available
                        logger.warning("All videos used, resetting for diversity")
                        used_video_ids.clear()
                        matching_content = content_matches[0]
                        used_video_ids.add(matching_content.video_id)
                
                if matching_content:
                    # Create segment in existing format
            segment = {
                        "script_segment": script_text,
                "clips": [
                    {
                                "video_id": matching_content.video_id,
                                "start": matching_content.start_time,
                                "end": matching_content.end_time,
                                "video": None  # Will be filled later if needed
                            }
                        ],
                        "audio": None,  # Will be filled later if needed
                        "duration": matching_content.duration
                    }
                    segments.append(segment)
                else:
                    # Create placeholder segment
                    segment = {
                        "script_segment": script_text,
                        "clips": [],
                        "audio": None,
                        "duration": 15.0  # Default duration
                    }
                    segments.append(segment)
            
            # Log diversity information
            unique_videos_used = len(used_video_ids)
            logger.info(f"✅ Parsed structured script into {len(segments)} segments")
            logger.info(f"🎯 Diversity: Used {unique_videos_used} unique videos")
            
            return segments
            
        except Exception as e:
            logger.error(f"❌ Failed to parse structured script to segments: {e}")
            return []

    async def parse_structured_script_to_segments_with_overlays(self, 
                                                              structured_script: Dict[str, Any],
                                                              content_matches: List[ContentMatch],
                                                              workout_requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse the structured script into segments with text overlays and video looping.
        
        Enhanced version that includes:
        - Text overlays for each exercise
        - Video looping for short clips
        - Better time management
        - Category-based organization
        """
        try:
            segments = []
            used_video_ids = set()  # Track used videos for diversity
            
            for i, segment_data in enumerate(structured_script.get("segments", [])):
                exercise_name = segment_data.get("exercise_name", "Exercise")
                reps = segment_data.get("reps", "10")
                rounds = segment_data.get("rounds", "1")
                form_cues = segment_data.get("form_cues", "")
                category = segment_data.get("category", "strength")
                text_overlay = segment_data.get("text_overlay", f"{exercise_name} - {reps} reps")
                loop_video = segment_data.get("loop_video", True)
                target_duration = segment_data.get("duration", 30.0)
                
                # Create script text
                script_text = f"{exercise_name} {reps} reps"
                if form_cues:
                    script_text += f" {form_cues}"
                
                # Find matching video content with diversity enforcement
                target_video_id = segment_data.get("target_video_id", "")
                matching_content = None
                
                if target_video_id:
                    # Try to find exact match
                    for match in content_matches:
                        if match.video_id == target_video_id:
                            matching_content = match
                            used_video_ids.add(match.video_id)
                            break
                
                # If no exact match or for diversity, select from unused videos
                if not matching_content and content_matches:
                    # Find best available content that hasn't been used yet
                    available_matches = [m for m in content_matches if m.video_id not in used_video_ids]
                    
                    if available_matches:
                        # Select the first available match
                        matching_content = available_matches[0]
                        used_video_ids.add(matching_content.video_id)
                    else:
                        # If all videos used, reset and use first available
                        logger.warning("All videos used, resetting for diversity")
                        used_video_ids.clear()
                        matching_content = content_matches[0]
                        used_video_ids.add(matching_content.video_id)
                
                if matching_content:
                    # Calculate video duration and looping
                    video_duration = matching_content.duration
                    loops_needed = max(1, int(target_duration / video_duration)) if loop_video else 1
                    
                    # Create segment with enhanced features
                    segment = {
                        "script_segment": script_text,
                        "category": category,
                        "text_overlay": text_overlay,
                        "loop_video": loop_video,
                        "loops_needed": loops_needed,
                        "clips": [
                            {
                                "video_id": matching_content.video_id,
                                "start": matching_content.start_time,
                                "end": matching_content.end_time,
                                "video": None,  # Will be filled later if needed
                                "loop_count": loops_needed
                            }
                        ],
                        "audio": None,  # Will be filled later if needed
                        "duration": target_duration
                    }
            segments.append(segment)
                else:
                    # Create placeholder segment
                    segment = {
                        "script_segment": script_text,
                        "category": category,
                        "text_overlay": text_overlay,
                        "loop_video": loop_video,
                        "loops_needed": 1,
                        "clips": [],
                        "audio": None,
                        "duration": target_duration
                    }
                    segments.append(segment)
            
            # Log diversity information
            unique_videos_used = len(used_video_ids)
            logger.info(f"✅ Parsed structured script into {len(segments)} segments with overlays")
            logger.info(f"🎯 Diversity: Used {unique_videos_used} unique videos")
            logger.info(f"📝 Categories: {list(set(s.get('category', 'unknown') for s in segments))}")
            
            return segments
            
        except Exception as e:
            logger.error(f"❌ Failed to parse structured script to segments with overlays: {e}")
            return []

    async def generate_compilation_json_with_requirements(self, 
                                                        content_matches: List[ContentMatch],
                                                        workout_requirements: Dict[str, Any],
                                                        user_requirements: str,
                                                        include_audio: bool = True,
                                                        include_clips: bool = True,
                                                        aspect_ratio: str = "9:16",
                                                        show_debug_overlay: bool = False) -> List[Dict[str, Any]]:
        """
        Generate complete compilation JSON using workout requirements for better structure.
        
        NEW FLOW:
        1. Collect all content context
        2. Generate structured compilation script using workout requirements
        3. Parse structured script to segments with text overlays and looping
        4. Add audio/clips to segments
        """
        
        # Step 1: Collect all content context
        content_context = await self.collect_content_context(content_matches)
        
        # Step 2: Generate structured compilation script using workout requirements
        structured_script = await self.generate_structured_compilation_script_with_requirements(
            content_matches, workout_requirements, user_requirements
        )
        
        # Step 3: Parse structured script to segments with enhanced features
        segments = await self.parse_structured_script_to_segments_with_overlays(
            structured_script, content_matches, workout_requirements
        )
        
        # Step 4: Add audio and clips
        for segment in segments:
            if include_audio:
                segment["audio"] = await self._generate_segment_audio(segment["script_segment"])
            if include_clips and segment.get("clips"):
                # Extract video clips for each segment
                for clip in segment["clips"]:
                    if clip.get("video_id"):
                        # Find matching content match
                        matching_match = None
                        for match in content_matches:
                            if match.video_id == clip["video_id"]:
                                matching_match = match
                                break
                        
                        if matching_match:
                            video_clip_obj = await self._extract_video_clip(
                                matching_match, aspect_ratio, target_duration=segment.get("duration", 15.0)
                            )
                            clip["video"] = video_clip_obj.video if video_clip_obj else None
        
        return segments

    async def generate_compilation_json(self, 
                                      content_matches: List[ContentMatch],
                                    user_requirements: str,
                                      include_audio: bool = True,
                                      include_clips: bool = True,
                                      aspect_ratio: str = "9:16",
                                      show_debug_overlay: bool = False) -> List[Dict[str, Any]]:
        """
        Generate complete compilation JSON with script segments, video clips, and audio.
        
        NEW FLOW:
        1. Collect all content context
        2. Generate structured compilation script
        3. Parse structured script to segments
        4. Add audio/clips to segments
        """
        
        # Step 1: Collect all content context
        content_context = await self.collect_content_context(content_matches)
        
        # Step 2: Generate structured compilation script
        structured_script = await self.generate_structured_compilation_script(
            content_matches, user_requirements
        )
        
        # Step 3: Parse structured script to segments
        segments = await self.parse_structured_script_to_segments(
            structured_script, content_matches
        )
        
        # Step 4: Add audio and clips
        for segment in segments:
            if include_audio:
                segment["audio"] = await self._generate_segment_audio(segment["script_segment"])
            if include_clips and segment.get("clips"):
                # Extract video clips for each segment
                for clip in segment["clips"]:
                    if clip.get("video_id"):
                        # Find matching content match
                        matching_match = None
                        for match in content_matches:
                            if match.video_id == clip["video_id"]:
                                matching_match = match
                                break
                        
                        if matching_match:
                            video_clip_obj = await self._extract_video_clip(
                                matching_match, aspect_ratio, target_duration=segment.get("duration", 15.0)
                            )
                            clip["video"] = video_clip_obj.video if video_clip_obj else None
            
        return segments
    
    async def _generate_script_structure(self, content_matches: List[ContentMatch], 
                                       user_requirements: str) -> List[str]:
        """Generate script segments using AI."""
        try:
            # Create summary of available content
            content_summary = self._summarize_content_matches(content_matches)
            
            # Generate AI prompt for script structure
            prompt = f"""
You are a fitness video script writer. Based on the user's requirements and available video content, create a structured workout script.

USER REQUIREMENTS: {user_requirements}

AVAILABLE CONTENT:
{content_summary}

Generate a JSON array of script segments. Each segment should be:
- 15-30 seconds of instructional narration directly to a single viewer.
- No intro/outro - just the exercises and instructions
- Do not talk like you are a coach, just tell the viewer what the exercise is and how many reps and sets to do.
- Try to use videos from different urls to make it more interesting. 
- Do not use any other text in the script, just the exercises and instructions.

Return ONLY a JSON array of strings, like:
[
  "Squat 10 reps be sure to get as low as you can while keeping your feet flat on the floor",
  "push ups 10 reps be sure to keep your elbows close to your body",
  "pike up 10 reps be sure to keep your elbows close to your body",
  "do 3 rounds of 10 reps each" 
  "end with a mobility stretch starting with a cat cow stretch for 8 breaths"
  "move into a cobras pose for 8 breaths"
  "end with a downward facing dog for 8 breaths"
]

Make it 3-5 segments total.
"""
            
            # Call OpenAI to generate script
            response = await self.connections.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a fitness video script writer. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            # Parse AI response
            script_text = response.choices[0].message.content.strip()
            
            # Clean up the response and parse JSON
            if script_text.startswith('```json'):
                script_text = script_text[7:-3]
            elif script_text.startswith('```'):
                script_text = script_text[3:-3]
            
            script_segments = json.loads(script_text)
            
            logger.info(f"✅ Generated {len(script_segments)} script segments")
            return script_segments
            
        except Exception as e:
            logger.error(f"❌ Failed to generate script structure: {e}")
            # Return fallback script segments
        return [
                "Start with gentle warm-up movements to prepare your body for exercise.",
                "Now let's move into the main exercises with proper form and control.",
                "Continue with steady movements, focusing on your breathing and technique.",
                "Finish with some light stretching to cool down and relax your muscles."
            ]
    
    def _summarize_content_matches(self, content_matches: List[ContentMatch]) -> str:
        """Create a summary of available content matches."""
        if not content_matches:
            return "No specific content available."
        
        summary_lines = []
        for i, match in enumerate(content_matches[:10]):  # Limit to first 10 matches
            summary_lines.append(f"- {match.content_text[:100]}...")
        
        return "\n".join(summary_lines)
    
    async def _generate_segment_audio(self, script_text: str) -> Optional[str]:
        """Generate audio for a single script segment."""
        try:
            # Generate audio using OpenAI TTS
            audio_base64 = await self.audio_generator.generate_single_audio(
                text=script_text,
                voice="alloy",
                high_quality=False
            )
            
            if audio_base64:
                logger.info(f"✅ Generated audio for segment: {script_text[:50]}...")
                return audio_base64
            else:
                logger.warning(f"⚠️ Audio generation failed for segment: {script_text[:50]}...")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to generate segment audio: {e}")
            return None
        
    async def _select_video_clips(self, script_text: str, content_matches: List[ContentMatch], 
                                aspect_ratio: str) -> List[VideoClip]:
        """Select and extract video clips for a script segment."""
        try:
            # Select 1-2 best matching clips for this segment
            relevant_matches = self._find_relevant_matches(script_text, content_matches)
            selected_matches = relevant_matches[:2]  # Max 2 clips per segment
            
            clips = []
            for match in selected_matches:
                # Extract video clip
                clip = await self._extract_video_clip(match, aspect_ratio)
                if clip:
                    clips.append(clip)
            
            # Ensure at least 1 clip
            if not clips and content_matches:
                # Fallback to first available match
                clip = await self._extract_video_clip(content_matches[0], aspect_ratio)
                if clip:
                    clips.append(clip)
            
            return clips
            
        except Exception as e:
            logger.error(f"❌ Failed to select video clips: {e}")
            return []
    
    def _find_relevant_matches(self, script_text: str, content_matches: List[ContentMatch]) -> List[ContentMatch]:
        """Find content matches most relevant to the script text."""
        script_lower = script_text.lower()
        
        # Score matches based on semantic similarity and variety
        scored_matches = []
        used_video_ids = set()
        
        for match in content_matches:
            content_lower = match.content_text.lower()
            
            # Skip if we already used this video (unless we have no choice)
            if match.video_id in used_video_ids and len(content_matches) > len(used_video_ids):
                continue
            
            # Score based on keyword overlap
            fitness_keywords = [
                'squat', 'push', 'plank', 'stretch', 'arm', 'leg', 'core', 'balance',
                'movement', 'exercise', 'position', 'muscle', 'strength', 'cardio',
                'warm', 'cool', 'breathe', 'hold', 'repeat', 'form', 'technique'
            ]
            
            # Base score from keyword matches
            score = 0
            for keyword in fitness_keywords:
                if keyword in script_lower and keyword in content_lower:
                    score += 1
            
            # Bonus for longer clips (more flexibility in extraction)
            duration = match.end_time - match.start_time
            if duration > 15:
                score += 1
            
            # Bonus for high-quality matches
            if match.relevance_score > 0.8:  # Changed from score to relevance_score
                score += 2
            
            # Penalty for reusing videos
            if match.video_id in used_video_ids:
                score -= 3
            
            scored_matches.append((score, match))
            used_video_ids.add(match.video_id)
        
        # Sort by score and return top matches
        scored_matches.sort(key=lambda x: x[0], reverse=True)
        return [match for score, match in scored_matches if score > 0]

    async def _generate_segment_script(self, scene_description: str,
                                   transcript_text: Optional[str],
                                   user_requirements: str) -> str:
        """Generate script text using scene description and transcript."""
        try:
            # Create prompt using both scene and transcript
            prompt = f"""
You are a fitness video script writer. Write a clear, natural script segment that accurately describes what is happening in this video clip.

SCENE DESCRIPTION:
{scene_description}

{"ORIGINAL AUDIO TRANSCRIPT:" + transcript_text if transcript_text else "NO TRANSCRIPT AVAILABLE"}

USER REQUIREMENTS:
{user_requirements}

Write a natural, conversational script that:
1. Accurately describes the exact exercise/movement shown in the video
2. Uses any form cues or technical details from the transcript if available
4. Is concise and focused (15-30 seconds of speech)
5. Does not include any movements or cues not shown in the video
6. No intro/outro - just the exercises and instructions
7. Do not talk like you are a coach, just tell the viewer what the exercise is and how many reps and sets to do.
8. Try to use videos from different urls to make it more interesting. 
9. Do not use any other text in the script, just the exercises and instructions.
10. Make sure that the script segement can work at any part of the video, not just the beginning.

Return ONLY the script text, no JSON or other formatting.
"""
            
            # Call OpenAI to generate script
            response = await self.connections.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a fitness video script writer. Return only the script text."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            # Get script text
            script_text = response.choices[0].message.content.strip()
            
            logger.info(f"✅ Generated script segment: {script_text[:50]}...")
            return script_text
            
        except Exception as e:
            logger.error(f"❌ Failed to generate segment script: {e}")
            # Return simple fallback using scene description
            return f"Now we'll do the following exercise: {scene_description}"

    async def _get_audio_duration(self, audio_base64: str) -> float:
        """Get accurate audio duration using multiple methods."""
        try:
            import tempfile
            import subprocess
            
            # Decode base64 audio
            audio_data = base64.b64decode(audio_base64)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name
            
            try:
                # Method 1: Use ffprobe to get stream duration
                cmd = [
                    'ffprobe', '-v', 'quiet', '-show_entries', 
                    'stream=duration', '-of', 'csv=p=0', temp_path
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0 and result.stdout.strip():
                    duration = float(result.stdout.strip())
                    if duration > 0:
                        logger.info(f"✅ Audio duration from stream: {duration:.2f}s")
                        return duration
                
                # Method 2: Use ffprobe to get format duration
                cmd = [
                    'ffprobe', '-v', 'quiet', '-show_entries', 
                    'format=duration', '-of', 'csv=p=0', temp_path
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0 and result.stdout.strip():
                    duration = float(result.stdout.strip())
                    if duration > 0:
                        logger.info(f"✅ Audio duration from format: {duration:.2f}s")
                        return duration
                
                # Method 3: Use ffmpeg to get duration from output
                cmd = [
                    'ffmpeg', '-i', temp_path, '-f', 'null', '-'
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                # Parse duration from ffmpeg output
                import re
                duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})', result.stderr)
                if duration_match:
                    hours = int(duration_match.group(1))
                    minutes = int(duration_match.group(2))
                    seconds = float(duration_match.group(3))
                    duration = hours * 3600 + minutes * 60 + seconds
                    logger.info(f"✅ Audio duration from ffmpeg: {duration:.2f}s")
                    return duration
                
                # Fallback: estimate from text length
                logger.warning("⚠️ Could not determine audio duration, using text estimate")
                return 15.0  # Default fallback
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"❌ Failed to get audio duration: {e}")
            return 15.0  # Default fallback

    async def _extract_video_clip(self, match: ContentMatch, aspect_ratio: str, target_duration: float = None) -> Optional[VideoClip]:
        """Extract and format a video clip."""
        try:
            # Get video data from database
            video_data = await self.video_db.get_video_base64(match.video_id)
            if not video_data:
                logger.warning(f"⚠️ Video not found: {match.video_id}")
                return None
            
            # Calculate clip duration and position
            total_duration = match.end_time - match.start_time
            
            # Use target_duration if provided (audio duration), otherwise use video logic
            if target_duration:
                # Audio is king - extract video to match audio duration
                clip_duration = target_duration
                # ALWAYS start from beginning of the matched segment for consistency
                start_time = match.start_time
                logger.info(f"✅ Extracting clip from {match.video_id} starting at {start_time:.2f}s for {clip_duration:.2f}s")
            else:
                # Legacy logic for when no target duration provided
                if total_duration > 15:
                    # For longer clips, take a random segment
                    import random
                    start_offset = random.uniform(0, total_duration - 10)
                    clip_duration = min(10.0, total_duration - start_offset)
                    start_time = match.start_time + start_offset
                else:
                    # For shorter clips, use the whole thing
                    start_time = match.start_time
                    clip_duration = min(total_duration, 10.0)
            
            # Create temporary file for processing
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                temp_file.write(base64.b64decode(video_data))
                temp_input_path = temp_file.name
            
            try:
                # Extract and format clip
                clip_base64 = await self._extract_and_format_clip(
                    temp_input_path, start_time, clip_duration, aspect_ratio
                )
                
                if clip_base64:
                    return VideoClip(
                        video_id=match.video_id,
                        start=start_time,
                        end=start_time + clip_duration,
                        video=clip_base64
                    )
                else:
                    return None
                    
            finally:
                # Clean up temporary file
                if os.path.exists(temp_input_path):
                    os.unlink(temp_input_path)
                    
        except Exception as e:
            logger.error(f"❌ Failed to extract video clip: {e}")
            return None
    
    async def _extract_and_format_clip(self, input_path: str, start_time: float, 
                                     duration: float, aspect_ratio: str) -> Optional[str]:
        """Extract and format video clip with proper aspect ratio."""
        try:
            # Calculate target width based on aspect ratio
            target_width = 720 if aspect_ratio == "square" else 405  # 405 for 9:16 (720x1280)
            
            # Scale to target aspect ratio
            if aspect_ratio == "9:16":
                scale_filter = "scale=406:-2"  # Even width for 9:16
            elif aspect_ratio == "square":
                scale_filter = "scale=540:540"  # Square format
            else:
                scale_filter = "scale=406:-2"  # Default to 9:16
            
            # Use existing video processing function
            base64_video = extract_and_downscale_scene(
                input_path,
                start_time,
                start_time + duration,
                target_width=target_width,
                scale_filter=scale_filter
            )
            
            if base64_video:
                return base64_video
            else:
                logger.warning(f"⚠️ Failed to extract clip: {start_time}-{start_time + duration}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to extract and format clip: {e}")
            return None
    
    async def _create_placeholder_clips(self, content_matches: List[ContentMatch], 
                                      count: int) -> List[VideoClip]:
        """Create placeholder clips without base64 data."""
        clips = []
        for i, match in enumerate(content_matches[:count]):
            clips.append(VideoClip(
                video_id=match.video_id,
                start=match.start_time,
                end=match.end_time,
                video=None  # No base64 data
            ))
        return clips 