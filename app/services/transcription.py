import os
import asyncio
import whisper
import cv2
from typing import List, Optional, Dict
from pathlib import Path
from ..core.errors import ProcessingError
from ..models.common import TranscriptSegment

class TranscriptionService:
    def __init__(self, model_size: str = "base"):
        """
        Initialize the transcription service.
        
        Args:
            model_size: Size of the Whisper model to use (tiny, base, small, medium, large)
        """
        self.model = None
        self.model_size = model_size
        
    async def load_model(self):
        """Load the Whisper model asynchronously."""
        if self.model is None:
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(None, whisper.load_model, self.model_size)
            
    async def transcribe_video(self, video_path: str, progress_callback: Optional[callable] = None) -> List[TranscriptSegment]:
        """
        Transcribe a video file using Whisper.
        
        Args:
            video_path: Path to the video file
            progress_callback: Optional callback function to report progress
            
        Returns:
            List of TranscriptSegment objects containing transcription data
            
        Raises:
            ProcessingError: If transcription fails
        """
        try:
            # Ensure model is loaded
            await self.load_model()
            
            # Get video duration using OpenCV
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ProcessingError(f"Could not open video file: {video_path}")
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else None
            cap.release()
            
            # Run transcription in a thread pool
            loop = asyncio.get_event_loop()
            
            def _transcribe():
                # Transcribe the video
                result = self.model.transcribe(
                    video_path,
                    verbose=False,
                    fp16=False  # Use CPU for better compatibility
                )
                
                # Convert to our segment format
                segments = []
                for segment in result["segments"]:
                    # Calculate progress based on segment end time or frame count
                    if progress_callback:
                        if duration:
                            progress = (segment["end"] / duration) * 100
                        else:
                            # Fallback to frame-based progress
                            progress = (len(segments) / len(result["segments"])) * 100
                        asyncio.run_coroutine_threadsafe(
                            progress_callback(progress),
                            loop
                        )
                    
                    transcript_segment = TranscriptSegment(
                        start=segment["start"],
                        end=segment["end"],
                        text=segment["text"].strip(),
                        confidence=segment.get("confidence", 0.0)
                    )
                    segments.append(transcript_segment)
                        
                return segments
                
            return await loop.run_in_executor(None, _transcribe)
            
        except Exception as e:
            raise ProcessingError(f"Failed to transcribe video: {str(e)}")
            
    async def transcribe_audio(self, audio_path: str, progress_callback: Optional[callable] = None) -> List[TranscriptSegment]:
        """
        Transcribe an audio file using Whisper.
        
        Args:
            audio_path: Path to the audio file
            progress_callback: Optional callback function to report progress
            
        Returns:
            List of TranscriptSegment objects containing transcription data
            
        Raises:
            ProcessingError: If transcription fails
        """
        return await self.transcribe_video(audio_path, progress_callback)
        
    def cleanup(self):
        """Clean up resources used by the service."""
        self.model = None  # Allow model to be garbage collected 