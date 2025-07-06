#!/usr/bin/env python3
"""
AI Scene Analysis using GPT-4 Vision with Transcript Integration
Analyzes extreme frames from scene detection to generate descriptions and tags
Enhanced with transcript data for richer, more accurate scene descriptions
"""

import os
import base64
import json
import asyncio
from typing import List, Dict, Optional
from openai import AsyncOpenAI
import aiofiles
from dotenv import load_dotenv
from app.ai_rate_limiter import get_rate_limiter, RateLimitType

# Load environment variables from .env file
load_dotenv()

# Initialize clients (will be set when needed)
openai_client = None
gemini_client = None

# Check which AI provider to use
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai").lower()  # Default to OpenAI
print(f"🤖 AI Provider: {AI_PROVIDER.upper()}")

# Import Gemini if needed
if AI_PROVIDER == "gemini":
    try:
        import google.generativeai as genai
        print("✅ Google Generative AI imported successfully")
    except ImportError:
        print("❌ Google Generative AI not installed. Install with: pip install google-generativeai")
        AI_PROVIDER = "openai"  # Fall back to OpenAI

def get_openai_client():
    """Get OpenAI client, initializing if needed."""
    global openai_client
    if openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        openai_client = AsyncOpenAI(api_key=api_key)
    return openai_client

def get_gemini_client():
    """Get Gemini client, initializing if needed."""
    global gemini_client
    if gemini_client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key not found. Set GEMINI_API_KEY environment variable.")
        genai.configure(api_key=api_key)
        gemini_client = genai.GenerativeModel('gemini-2.5-flash-lite-preview-06-17')
        print("✅ Gemini 2.0 Flash Experimental client initialized")
    return gemini_client

async def encode_image_to_base64(image_path: str) -> str:
    """Convert image file to base64 string for GPT-4 Vision."""
    try:
        async with aiofiles.open(image_path, "rb") as image_file:
            image_data = await image_file.read()
            return base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image {image_path}: {e}")
        return ""

def find_relevant_transcript_segments(transcript_data: List[Dict], start_time: float, end_time: float) -> str:
    """
    Find transcript segments that overlap with the scene timeframe.
    
    Args:
        transcript_data: List of transcript segments with start/end times
        start_time: Scene start time in seconds
        end_time: Scene end time in seconds
        
    Returns:
        Combined text from overlapping transcript segments
    """
    if not transcript_data:
        return ""
    
    relevant_segments = []
    
    for segment in transcript_data:
        seg_start = segment.get('start', 0.0)
        seg_end = segment.get('end', 0.0)
        
        # Check if segment overlaps with scene timeframe
        if seg_start < end_time and seg_end > start_time:
            relevant_segments.append(segment.get('text', '').strip())
    
    return " ".join(relevant_segments).strip()

def create_video_context_from_scenes(scenes_data: List[Dict], transcript_data: Optional[List[Dict]] = None) -> str:
    """
    Create video-level context from existing scene descriptions and transcript.
    This provides comprehensive context for enhanced AI analysis.
    
    Args:
        scenes_data: List of scene dictionaries with existing descriptions
        transcript_data: Optional transcript segments
        
    Returns:
        Compiled video context string, filtered of AI prompts
    """
    context_parts = []
    
    # Add full transcript context if available
    if transcript_data:
        full_transcript = " ".join([seg.get('text', '').strip() for seg in transcript_data]).strip()
        if full_transcript:
            context_parts.append(f"FULL TRANSCRIPT: {full_transcript}")
    
    # Add scene descriptions if available
    if scenes_data:
        scene_descriptions = []
        for i, scene in enumerate(scenes_data):
            # Get existing description - could be from 'ai_description' or 'description' field
            description = scene.get('ai_description') or scene.get('description', '')
            if description:
                # Filter out AI prompts and system text - keep only the actual description
                filtered_description = _filter_ai_prompts(description)
                if filtered_description:
                    start_time = scene.get('start_time', 0)
                    end_time = scene.get('end_time', 0)
                    scene_descriptions.append(f"Scene {i+1} ({start_time:.1f}s-{end_time:.1f}s): {filtered_description}")
        
        if scene_descriptions:
            context_parts.append(f"PREVIOUS SCENE ANALYSIS: {' | '.join(scene_descriptions)}")
    
    return " | ".join(context_parts) if context_parts else ""

def _filter_ai_prompts(text: str) -> str:
    """
    Filter out AI prompts and system text from descriptions, keeping only the actual content.
    
    Args:
        text: Raw text that may contain AI prompts
        
    Returns:
        Filtered text with prompts removed
    """
    if not text:
        return ""
    
    # Common AI prompt patterns to remove
    prompt_patterns = [
        "analyze this",
        "provide a description",
        "describe the movement",
        "what exercise",
        "respond in json",
        "format:",
        "please analyze",
        "based on the frames",
        "movement/exercise",
        "exercise type",
        "muscle groups",
        "movement patterns"
    ]
    
    # Split into sentences and filter
    sentences = text.split('.')
    filtered_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # Check if sentence contains prompt patterns
        is_prompt = any(pattern in sentence.lower() for pattern in prompt_patterns)
        
        # Keep sentences that are actual descriptions (not prompts)
        if not is_prompt and len(sentence) > 20:  # Reasonable length for actual descriptions
            filtered_sentences.append(sentence)
    
    result = '. '.join(filtered_sentences)
    if result and not result.endswith('.'):
        result += '.'
    
    return result.strip()

async def analyze_scene_with_gemini(extreme_frames: List[Dict], scene_index: int, 
                                   start_time: float, end_time: float,
                                   transcript_data: Optional[List[Dict]] = None,
                                   video_context: Optional[str] = None) -> Dict:
    """
    Analyze a scene's extreme frames using Gemini 2.0 Flash with optional transcript and video context.
    
    Args:
        extreme_frames: List of extreme frame data with frame_path, frame_type, etc.
        scene_index: Scene number for reference
        start_time: Scene start time in seconds
        end_time: Scene end time in seconds
        transcript_data: Optional transcript segments for context
        video_context: Optional video-level context from previous scene analysis
        
    Returns:
        Dict with AI analysis: description, tags, and scene metadata
    """
    
    # Filter to only the key extreme frames (start, valley, peak, end)
    key_frames = [f for f in extreme_frames if f['frame_type'] in ['start', 'valley', 'peak', 'end']]
    
    if not key_frames:
        return {
            "scene_index": scene_index,
            "start_time": start_time,
            "end_time": end_time,
            "description": "No key frames available for analysis",
            "tags": [],
            "analysis_success": False,
            "has_transcript": bool(transcript_data),
            "scene_transcript": None
        }
    
    # Extract relevant transcript for this scene
    scene_transcript = ""
    if transcript_data:
        scene_transcript = find_relevant_transcript_segments(transcript_data, start_time, end_time)
    
    transcript_context = f" (transcript available)" if scene_transcript else " (no transcript)"
    print(f"🤖 Analyzing scene {scene_index + 1} with {len(key_frames)} key frames using Gemini{transcript_context}...")
    
    try:
        # Get Gemini client
        model = get_gemini_client()
        
        # Prepare images for Gemini
        image_parts = []
        for frame in key_frames:
            try:
                # Read image file
                async with aiofiles.open(frame['frame_path'], "rb") as image_file:
                    image_data = await image_file.read()
                    image_parts.append({
                        "mime_type": "image/jpeg",
                        "data": image_data
                    })
            except Exception as e:
                print(f"Error reading image {frame['frame_path']}: {e}")
                continue
        
        if not image_parts:
            return {
                "scene_index": scene_index,
                "start_time": start_time,
                "end_time": end_time,
                "description": "No valid images available for analysis",
                "tags": [],
                "analysis_success": False,
                "has_transcript": bool(scene_transcript),
                "scene_transcript": scene_transcript if scene_transcript else None
            }
        
        # Build context for the prompt
        context_parts = []
        if scene_transcript:
            context_parts.append(f"TRANSCRIPT: {scene_transcript}")
        if video_context:
            context_parts.append(f"VIDEO CONTEXT: {video_context}")
        
        context_str = " | ".join(context_parts)
        context_prompt = f" Additional context: {context_str}" if context_str else ""
        
        # Create the prompt
        prompt = f"""Analyze these {len(image_parts)} key frames from a video scene (timestamps: {start_time:.1f}s to {end_time:.1f}s).{context_prompt}

Please provide:
1. A detailed description of the movement/exercise being performed, including:
   - Step-by-step instructions on how to perform the action
   - The benefits of the exercise and its usefulness
   - Any prerequisites or safety considerations to keep in mind
2. 3-5 relevant tags that describe the exercise, such as:
   - Exercise type (e.g., strength, cardio, flexibility)
   - Target muscle groups involved (e.g., arms, legs, core)
   - Movement patterns (e.g., push, pull, squat)

Respond in JSON format:
{{
    "description": "detailed description of the movement/exercise",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}"""
        
        # Make the API call with rate limiting
        rate_limiter = get_rate_limiter("gemini")
        
        # Estimate tokens for this request (base + image tokens)
        estimated_tokens = 1000 + (len(image_parts) * 1500)  # ~1500 tokens per image for Gemini
        
        async def make_gemini_call():
            return await asyncio.to_thread(
                model.generate_content,
                [prompt] + image_parts
            )
        
        response = await rate_limiter.execute_with_rate_limiting(
            make_gemini_call,
            estimated_tokens=estimated_tokens
        )
        
        # Parse the response
        response_text = response.text.strip()
        
        # Try to extract JSON from the response
        try:
            # Look for JSON in the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response_text[json_start:json_end]
                analysis = json.loads(json_str)
                
                description = analysis.get('description', '').strip()
                tags = analysis.get('tags', [])
                
                # Ensure tags is a list
                if isinstance(tags, str):
                    tags = [tags]
                elif not isinstance(tags, list):
                    tags = []
                
                # Clean up tags
                tags = [tag.strip().lower() for tag in tags if tag and isinstance(tag, str)]
                tags = [tag for tag in tags if len(tag) > 0]  # Remove empty tags
                
                return {
                    "scene_index": scene_index,
                    "start_time": start_time,
                    "end_time": end_time,
                    "description": description,
                    "tags": tags,
                    "analysis_success": True,
                    "has_transcript": bool(scene_transcript),
                    "has_video_context": bool(video_context),
                    "scene_transcript": scene_transcript if scene_transcript else None
                }
            else:
                # Fallback if no JSON found
                return {
                    "scene_index": scene_index,
                    "start_time": start_time,
                    "end_time": end_time,
                    "description": response_text,
                    "tags": [],
                    "analysis_success": True,
                    "has_transcript": bool(scene_transcript),
                    "has_video_context": bool(video_context),
                    "scene_transcript": scene_transcript if scene_transcript else None
                }
                
        except json.JSONDecodeError:
            # Fallback to raw response if JSON parsing fails
            return {
                "scene_index": scene_index,
                "start_time": start_time,
                "end_time": end_time,
                "description": response_text,
                "tags": [],
                "analysis_success": True,
                "has_transcript": bool(scene_transcript),
                "has_video_context": bool(video_context),
                "scene_transcript": scene_transcript if scene_transcript else None
            }
            
    except Exception as e:
        print(f"Error in Gemini analysis for scene {scene_index}: {e}")
        return {
            "scene_index": scene_index,
            "start_time": start_time,
            "end_time": end_time,
            "description": f"Analysis failed: {str(e)}",
            "tags": [],
            "analysis_success": False,
            "has_transcript": bool(scene_transcript) if transcript_data else False,
            "scene_transcript": scene_transcript if scene_transcript else None
        }

async def analyze_scene_with_gpt4_vision(extreme_frames: List[Dict], scene_index: int, 
                                       start_time: float, end_time: float,
                                       transcript_data: Optional[List[Dict]] = None,
                                       video_context: Optional[str] = None) -> Dict:
    """
    Analyze a scene's extreme frames using GPT-4 Vision with optional transcript and video context.
    
    Args:
        extreme_frames: List of extreme frame data with frame_path, frame_type, etc.
        scene_index: Scene number for reference
        start_time: Scene start time in seconds
        end_time: Scene end time in seconds
        transcript_data: Optional transcript segments for context
        video_context: Optional video-level context from previous scene analysis
        
    Returns:
        Dict with AI analysis: description, tags, and scene metadata
    """
    
    # Filter to only the key extreme frames (start, valley, peak, end)
    key_frames = [f for f in extreme_frames if f['frame_type'] in ['start', 'valley', 'peak', 'end']]
    
    if not key_frames:
        return {
            "scene_index": scene_index,
            "start_time": start_time,
            "end_time": end_time,
            "description": "No key frames available for analysis",
            "tags": [],
            "analysis_success": False
        }
    
    # Extract relevant transcript for this scene
    scene_transcript = ""
    if transcript_data:
        scene_transcript = find_relevant_transcript_segments(transcript_data, start_time, end_time)
    
    transcript_context = f" (transcript available)" if scene_transcript else " (no transcript)"
    print(f"🤖 Analyzing scene {scene_index + 1} with {len(key_frames)} key frames{transcript_context}...")
    
    try:
        # Encode all key frames to base64
        encoded_frames = []
        for frame in key_frames:
            if os.path.exists(frame['frame_path']):
                encoded_image = await encode_image_to_base64(frame['frame_path'])
                if encoded_image:
                    encoded_frames.append({
                        "type": frame['frame_type'],
                        "timestamp": frame['timestamp'],
                        "image_data": encoded_image
                    })
        
        if not encoded_frames:
            return {
                "scene_index": scene_index,
                "start_time": start_time,
                "end_time": end_time,
                "description": "Failed to encode frames for analysis",
                "tags": [],
                "analysis_success": False
            }
        
        # Build context-aware prompt
        base_prompt = f"""Analyze this sequence of {len(encoded_frames)} frames from a mobility/exercise video scene.

The frames represent key movement positions:
- START: Beginning position  
- VALLEY: One extreme of the movement
- PEAK: Opposite extreme of the movement
- END: Final position

Scene timing: {start_time:.2f}s - {end_time:.2f}s"""

        # Add transcript context if available
        if scene_transcript:
            base_prompt += f"""

TRANSCRIPT CONTEXT for this scene:
"{scene_transcript}"

Use this transcript to better understand what exercise/movement is being performed and provide more accurate descriptions."""
        else:
            base_prompt += "\n\nNo transcript is available for this scene."
        
        # Add video-level context if available
        if video_context:
            base_prompt += f"""

VIDEO CONTEXT (full video understanding):
{video_context}

Use this broader context to understand how this scene fits into the overall video flow and exercise sequence."""

        base_prompt += """

Please analyze what exercise or movement is being performed and provide:

1. A detailed description of the movement/exercise being performed, including:
   - Step-by-step instructions on how to perform the action
   - The benefits of the exercise and its usefulness
   - Any prerequisites or safety considerations to keep in mind
2. 3-5 relevant tags that describe the exercise, such as:
   - Exercise type (e.g., strength, cardio, flexibility)
   - Target muscle groups involved (e.g., arms, legs, core)
   - Movement patterns (e.g., push, pull, squat)

Respond in this exact JSON format:
{
    "description": "Detailed description of the movement/exercise being performed",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}"""

        # Prepare GPT-4 Vision prompt
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": base_prompt
                    }
                ]
            }
        ]
        
        # Add each frame image
        for i, frame in enumerate(encoded_frames):
            messages[0]["content"].append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{frame['image_data']}"
                }
            })
            messages[0]["content"].append({
                "type": "text", 
                "text": f"Frame {i+1}: {frame['type'].upper()} position at {frame['timestamp']:.2f}s"
            })
        
        # Call GPT-4 Vision API with rate limiting
        openai_client = get_openai_client()
        rate_limiter = get_rate_limiter("openai")
        
        # Estimate tokens for this request (base + image tokens)
        estimated_tokens = 1000 + (len(encoded_frames) * 2000)  # ~2000 tokens per image
        
        async def make_openai_call():
            return await openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=500,
                temperature=0.1
            )
        
        response = await rate_limiter.execute_with_rate_limiting(
            make_openai_call,
            estimated_tokens=estimated_tokens
        )
        
        # Parse the response
        response_text = response.choices[0].message.content.strip()
        
        # Try to extract JSON from the response
        try:
            # Look for JSON in the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                analysis_data = json.loads(json_text)
                
                return {
                    "scene_index": scene_index,
                    "start_time": start_time,
                    "end_time": end_time,
                    "description": analysis_data.get("description", ""),
                    "tags": analysis_data.get("tags", [])[:5],  # Ensure max 5 tags
                    "analysis_success": True,
                    "has_transcript": bool(scene_transcript),
                    "scene_transcript": scene_transcript if scene_transcript else None,
                    "raw_response": response_text
                }
            else:
                # Fallback: extract description and tags manually
                lines = response_text.split('\n')
                description = ""
                tags = []
                
                for line in lines:
                    if 'description' in line.lower() and ':' in line:
                        description = line.split(':', 1)[1].strip().strip('"')
                    elif 'tag' in line.lower() and '[' in line:
                        # Try to extract tags from array format
                        tag_start = line.find('[')
                        tag_end = line.find(']')
                        if tag_start >= 0 and tag_end > tag_start:
                            tag_text = line[tag_start+1:tag_end]
                            tags = [t.strip().strip('"') for t in tag_text.split(',')]
                
                return {
                    "scene_index": scene_index,
                    "start_time": start_time,
                    "end_time": end_time,
                    "description": description or "Movement analysis completed",
                    "tags": tags[:5] if tags else ["exercise", "movement", "mobility", "fitness", "training"],
                    "analysis_success": True,
                    "has_transcript": bool(scene_transcript),
                    "scene_transcript": scene_transcript if scene_transcript else None,
                    "raw_response": response_text
                }
                
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Raw response: {response_text}")
            
            return {
                "scene_index": scene_index,
                "start_time": start_time,
                "end_time": end_time,
                "description": "AI analysis completed but format parsing failed",
                "tags": ["exercise", "movement", "mobility", "fitness", "training"],
                "analysis_success": False,
                "has_transcript": bool(scene_transcript),
                "scene_transcript": scene_transcript if scene_transcript else None,
                "raw_response": response_text
            }
            
    except Exception as e:
        print(f"Error in GPT-4 Vision analysis: {e}")
        return {
            "scene_index": scene_index,
            "start_time": start_time,
            "end_time": end_time,
            "description": f"Analysis failed: {str(e)}",
            "tags": [],
            "analysis_success": False,
            "has_transcript": bool(scene_transcript) if transcript_data else False,
            "scene_transcript": scene_transcript if scene_transcript else None
        }

async def analyze_scene_with_ai(extreme_frames: List[Dict], scene_index: int, 
                               start_time: float, end_time: float,
                               transcript_data: Optional[List[Dict]] = None,
                               video_context: Optional[str] = None) -> Dict:
    """
    Analyze a scene using the configured AI provider (OpenAI or Gemini).
    
    Args:
        extreme_frames: List of extreme frame data with frame_path, frame_type, etc.
        scene_index: Scene number for reference
        start_time: Scene start time in seconds
        end_time: Scene end time in seconds
        transcript_data: Optional transcript segments for context
        video_context: Optional video-level context from previous scene analysis
        
    Returns:
        Dict with AI analysis: description, tags, and scene metadata
    """
    
    if AI_PROVIDER == "gemini":
        return await analyze_scene_with_gemini(
            extreme_frames, scene_index, start_time, end_time, 
            transcript_data, video_context
        )
    else:
        return await analyze_scene_with_gpt4_vision(
            extreme_frames, scene_index, start_time, end_time, 
            transcript_data, video_context
        )

async def analyze_all_scenes_with_ai(scenes_data: List[Dict], transcript_data: Optional[List[Dict]] = None, 
                                   existing_scenes: Optional[List[Dict]] = None) -> List[Dict]:
    """
    Analyze all scenes using GPT-4 Vision with optional transcript and video context.
    
    Args:
        scenes_data: List of scene dictionaries from enhanced scene detection
        transcript_data: Optional list of transcript segments for context
        existing_scenes: Optional existing scene descriptions for video-level context
        
    Returns:
        List of scene dictionaries with AI analysis added
    """
    transcript_status = f" with transcript context" if transcript_data else ""
    video_context_status = f" with video context" if existing_scenes else ""
    context_info = f"{transcript_status}{video_context_status}" if transcript_status or video_context_status else " (visual only)"
    
    print(f"🧠 Starting AI analysis of {len(scenes_data)} scenes{context_info}...")
    
    # Create video-level context from existing scenes and transcript
    video_context = None
    if existing_scenes or transcript_data:
        video_context = create_video_context_from_scenes(existing_scenes or [], transcript_data)
        if video_context:
            print(f"📚 Created video context from {len(existing_scenes) if existing_scenes else 0} existing scenes and {'transcript' if transcript_data else 'no transcript'}")
    
    # Analyze scenes concurrently (but limit concurrency to avoid API limits)
    semaphore = asyncio.Semaphore(3)  # Max 3 concurrent API calls
    
    async def analyze_single_scene(scene_data: Dict, index: int) -> Dict:
        async with semaphore:
            analysis = await analyze_scene_with_ai(
                scene_data['extreme_frames'],
                index,
                scene_data['start_time'],
                scene_data['end_time'],
                transcript_data,
                video_context
            )
            
            # Merge the analysis with the original scene data
            return {
                **scene_data,
                "ai_description": analysis['description'],
                "ai_tags": analysis['tags'],
                "analysis_success": analysis['analysis_success'],
                "has_transcript": analysis.get('has_transcript', False),
                "scene_transcript": analysis.get('scene_transcript'),
                "has_video_context": bool(video_context)
            }
    
    # Process all scenes
    tasks = [analyze_single_scene(scene, i) for i, scene in enumerate(scenes_data)]
    analyzed_scenes = await asyncio.gather(*tasks)
    
    success_count = sum(1 for scene in analyzed_scenes if scene.get('analysis_success', False))
    transcript_count = sum(1 for scene in analyzed_scenes if scene.get('has_transcript', False))
    video_context_count = sum(1 for scene in analyzed_scenes if scene.get('has_video_context', False))
    
    print(f"✅ Completed AI analysis of {len(analyzed_scenes)} scenes")
    print(f"   📈 Success rate: {success_count}/{len(analyzed_scenes)} scenes")
    if transcript_data:
        print(f"   📝 Transcript context: {transcript_count}/{len(analyzed_scenes)} scenes")
    if video_context:
        print(f"   🎬 Video context: {video_context_count}/{len(analyzed_scenes)} scenes")
    
    return analyzed_scenes

async def cleanup_frame_images(scenes_data: List[Dict]) -> None:
    """
    Delete all the frame image files after AI analysis is complete.
    
    Args:
        scenes_data: List of scene dictionaries containing frame paths
    """
    print("🧹 Cleaning up frame images...")
    
    deleted_count = 0
    error_count = 0
    
    for scene in scenes_data:
        for frame in scene.get('extreme_frames', []):
            frame_path = frame.get('frame_path')
            if frame_path and os.path.exists(frame_path):
                try:
                    os.remove(frame_path)
                    deleted_count += 1
                except Exception as e:
                    print(f"Error deleting {frame_path}: {e}")
                    error_count += 1
    
    print(f"🗑️  Deleted {deleted_count} frame images")
    if error_count > 0:
        print(f"⚠️  Failed to delete {error_count} files")
    
    # Try to remove empty directories
    try:
        # Get the parent directory of frame files
        if scenes_data and scenes_data[0].get('extreme_frames'):
            first_frame_path = scenes_data[0]['extreme_frames'][0].get('frame_path')
            if first_frame_path:
                frames_dir = os.path.dirname(first_frame_path)
                if os.path.exists(frames_dir) and not os.listdir(frames_dir):
                    os.rmdir(frames_dir)
                    print(f"🗂️  Removed empty frames directory: {frames_dir}")
    except Exception as e:
        print(f"Note: Could not remove frames directory: {e}")

# Main function for testing
async def test_ai_analysis():
    """Test function for AI scene analysis."""
    # This would be called with actual scene data from enhanced scene detection
    print("🧪 AI Scene Analysis Test - requires actual scene data from scene detection")
    print("Use this module by calling analyze_all_scenes_with_ai(scenes_data)")

if __name__ == "__main__":
    asyncio.run(test_ai_analysis()) 