import whisper
import logging
import subprocess
import os

# Set up logger
logger = logging.getLogger(__name__)

def _check_audio_stream(video_path: str) -> bool:
    """Check if video file has an audio stream."""
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-select_streams', 'a:0', 
            '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.returncode == 0 and 'audio' in result.stdout
    except Exception as e:
        logger.warning(f"Failed to check audio stream: {e}")
        return False

def transcribe_audio(audio_path: str, model_size: str = 'base'):
    logger.info(f"🎤 Starting transcription with model: {model_size}")
    logger.info(f"📁 Video file: {audio_path}")
    
    # Check if video has audio stream
    if not _check_audio_stream(audio_path):
        logger.info("🔇 No audio stream detected in video - skipping transcription")
        return []
    
    try:
        model = whisper.load_model(model_size)
        result = model.transcribe(audio_path)
    except Exception as e:
        logger.error(f"❌ Transcription failed: {e}")
        if "Failed to load audio" in str(e) or "does not contain any stream" in str(e):
            logger.info("🔇 Video appears to have no audio - returning empty transcript")
            return []
        raise
    
    # Log the full transcript text
    full_text = result.get('text', '')
    logger.info(f"📝 FULL TRANSCRIPT:\n{full_text}")
    
    # Process segments
    segments = [
        {'start': seg['start'], 'end': seg['end'], 'text': seg['text']}
        for seg in result['segments']
    ]
    
    # Log detailed segment information
    logger.info(f"🔢 Total segments: {len(segments)}")
    logger.info("⏱️  TRANSCRIPT SEGMENTS:")
    
    for i, seg in enumerate(segments):
        start_time = seg['start']
        end_time = seg['end']
        duration = end_time - start_time
        text = seg['text'].strip()
        
        logger.info(f"  [{i+1:2d}] {start_time:6.2f}s - {end_time:6.2f}s ({duration:5.2f}s): {text}")
    
    # Log transcript statistics
    total_duration = segments[-1]['end'] if segments else 0
    logger.info(f"📊 TRANSCRIPT STATS:")
    logger.info(f"   • Total duration: {total_duration:.2f} seconds")
    logger.info(f"   • Total segments: {len(segments)}")
    logger.info(f"   • Average segment length: {total_duration/len(segments):.2f}s" if segments else "   • No segments")
    logger.info(f"   • Total characters: {len(full_text)}")
    logger.info(f"   • Words: {len(full_text.split())}")
    
    return segments
