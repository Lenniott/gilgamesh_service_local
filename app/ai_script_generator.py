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
    
    async def generate_compilation_json(self, 
                                      content_matches: List[ContentMatch],
                                    user_requirements: str,
                                      include_audio: bool = True,
                                      include_clips: bool = True,
                                      aspect_ratio: str = "9:16",
                                      show_debug_overlay: bool = False) -> List[Dict[str, Any]]:
        """
        Generate complete compilation JSON with script segments, video clips, and audio.
        
        Args:
            content_matches: List of relevant content matches from search
            user_requirements: User requirements for the compilation
            include_audio: Whether to include base64 audio in JSON
            include_clips: Whether to include base64 clips in JSON
            aspect_ratio: Target aspect ratio ("square" or "9:16")
            show_debug_overlay: Whether to show video ID overlay for debugging
            
        Returns:
            List of compilation segments matching vision doc format
        """
        
        # Process each content match into a segment
        segments = []
        used_video_ids = set()
        
        # Group matches by video_id and timestamp
        grouped_matches = {}
        for match in content_matches:
            key = (match.video_id, match.start_time, match.end_time)
            if key not in grouped_matches:
                grouped_matches[key] = {"scene": None, "transcript": None}
            grouped_matches[key][match.segment_type] = match
        
        # Process each group
        for (video_id, start_time, end_time), matches in grouped_matches.items():
            # Skip if we've already used this video too many times
            if video_id in used_video_ids and len(used_video_ids) > 3:
                continue
            
            scene_match = matches["scene"]
            transcript_match = matches["transcript"]
            
            # Skip if we don't have a scene description
            if not scene_match:
                continue
            
            # Generate script using both scene and transcript if available
            script = await self._generate_segment_script(
                scene_description=scene_match.content_text,
                transcript_text=transcript_match.content_text if transcript_match else None,
                user_requirements=user_requirements
            )
            
            # Generate audio for the script
            audio_base64 = await self.audio_generator.generate_single_audio(script, voice="alloy", high_quality=False) if include_audio else None
            
            # Calculate duration based on AUDIO, not video clip
            # Audio is king - video clips will loop/trim to match audio duration
            if audio_base64:
                # Get accurate audio duration using multiple methods
                audio_duration = await self._get_audio_duration(audio_base64)
                duration = audio_duration
            else:
                # Fallback to video clip duration if no audio
                duration = end_time - start_time
            
            # Extract video clip if needed
            video_clip_obj = await self._extract_video_clip(scene_match, aspect_ratio, target_duration=duration) if include_clips else None
            video_clip_base64 = video_clip_obj.video if video_clip_obj else None
            
            # Create segment with clips array format
            segment = {
                "script_segment": script,
                "clips": [
                    {
                        "video_id": video_id,
                        "start": start_time,
                        "end": end_time,
                        "video": video_clip_base64
                    }
                ],
                "audio": audio_base64,
                "duration": duration
            }
            
            segments.append(segment)
            used_video_ids.add(video_id)
            
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
    
    async def _generate_segment_audio(self, script_text: str) -> Optional[Dict[str, Any]]:
        """Generate audio for a single script segment."""
        try:
            # Generate audio using OpenAI TTS
            audio_base64 = await self.audio_generator.generate_single_audio(
                text=script_text,
                voice="alloy",
                high_quality=False
            )
            
            if audio_base64:
                # Estimate duration based on text length (rough approximation)
                # Average speaking rate: ~150 words per minute
                word_count = len(script_text.split())
                duration = max(5.0, (word_count / 150) * 60)  # Min 5 seconds
                
                return {
                    "audio_base64": audio_base64,
                    "duration": duration
                }
            else:
                logger.warning(f"⚠️ Audio generation failed for segment: {script_text[:50]}...")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to generate audio for segment: {e}")
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
            
            # Use existing video processing function
            base64_video = extract_and_downscale_scene(
                input_path,
                start_time,
                start_time + duration,
                target_width=target_width
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