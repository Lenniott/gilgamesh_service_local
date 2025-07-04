#!/usr/bin/env python3
"""
AI Scene Analysis using GPT-4 Vision
Analyzes extreme frames from scene detection to generate descriptions and tags
"""

import os
import base64
import json
import asyncio
from typing import List, Dict, Optional
from openai import AsyncOpenAI
import aiofiles
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client (will be set when needed)
client = None

def get_openai_client():
    """Get OpenAI client, initializing if needed."""
    global client
    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        client = AsyncOpenAI(api_key=api_key)
    return client

async def encode_image_to_base64(image_path: str) -> str:
    """Convert image file to base64 string for GPT-4 Vision."""
    try:
        async with aiofiles.open(image_path, "rb") as image_file:
            image_data = await image_file.read()
            return base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image {image_path}: {e}")
        return ""

async def analyze_scene_with_gpt4_vision(extreme_frames: List[Dict], scene_index: int, 
                                       start_time: float, end_time: float) -> Dict:
    """
    Analyze a scene's extreme frames using GPT-4 Vision.
    
    Args:
        extreme_frames: List of extreme frame data with frame_path, frame_type, etc.
        scene_index: Scene number for reference
        start_time: Scene start time in seconds
        end_time: Scene end time in seconds
        
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
    
    print(f"🤖 Analyzing scene {scene_index + 1} with {len(key_frames)} key frames using GPT-4 Vision...")
    
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
        
        # Prepare GPT-4 Vision prompt
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""Analyze this sequence of {len(encoded_frames)} frames from a mobility/exercise video scene.

The frames represent key movement positions:
- START: Beginning position  
- VALLEY: One extreme of the movement
- PEAK: Opposite extreme of the movement
- END: Final position

Please analyze what exercise or movement is being performed and provide:

1. A detailed description (2-3 sentences) of the movement/exercise being performed
2. Exactly 5 relevant tags (exercise type, muscle groups, movement patterns, etc.)

Respond in this exact JSON format:
{{
    "description": "Detailed description of the movement/exercise being performed",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}

Scene timing: {start_time:.2f}s - {end_time:.2f}s"""
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
        
        # Call GPT-4 Vision API
        openai_client = get_openai_client()
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=500,
            temperature=0.1
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
            "analysis_success": False
        }

async def analyze_all_scenes_with_ai(scenes_data: List[Dict]) -> List[Dict]:
    """
    Analyze all scenes using GPT-4 Vision.
    
    Args:
        scenes_data: List of scene dictionaries from enhanced scene detection
        
    Returns:
        List of scene dictionaries with AI analysis added
    """
    print(f"🧠 Starting AI analysis of {len(scenes_data)} scenes...")
    
    # Analyze scenes concurrently (but limit concurrency to avoid API limits)
    semaphore = asyncio.Semaphore(3)  # Max 3 concurrent API calls
    
    async def analyze_single_scene(scene_data: Dict, index: int) -> Dict:
        async with semaphore:
            analysis = await analyze_scene_with_gpt4_vision(
                scene_data['extreme_frames'],
                index,
                scene_data['start_time'],
                scene_data['end_time']
            )
            
            # Merge the analysis with the original scene data
            return {
                **scene_data,
                "ai_description": analysis['description'],
                "ai_tags": analysis['tags'],
                "analysis_success": analysis['analysis_success']
            }
    
    # Process all scenes
    tasks = [analyze_single_scene(scene, i) for i, scene in enumerate(scenes_data)]
    analyzed_scenes = await asyncio.gather(*tasks)
    
    print(f"✅ Completed AI analysis of {len(analyzed_scenes)} scenes")
    
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