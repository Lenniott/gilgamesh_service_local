import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.transcription import TranscriptionService
from app.core.errors import ProcessingError
from app.models.common import TranscriptSegment

@pytest.fixture
def transcription_service():
    return TranscriptionService(model_size="tiny")  # Use tiny model for faster tests

class TestTranscriptionService:
    @pytest.mark.asyncio
    async def test_load_model(self, transcription_service):
        """Test model loading."""
        with patch('whisper.load_model') as mock_load:
            mock_model = Mock()
            mock_load.return_value = mock_model
            
            await transcription_service.load_model()
            
            mock_load.assert_called_once_with("tiny")
            assert transcription_service.model == mock_model
            
    @pytest.mark.asyncio
    async def test_load_model_cached(self, transcription_service):
        """Test that model is only loaded once."""
        with patch('whisper.load_model') as mock_load:
            mock_model = Mock()
            mock_load.return_value = mock_model
            
            # Load model twice
            await transcription_service.load_model()
            await transcription_service.load_model()
            
            # Should only be called once
            mock_load.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_transcribe_video_success(self, transcription_service):
        """Test successful video transcription."""
        mock_segments = [
            {"start": 0.0, "end": 2.0, "text": "First segment", "confidence": 0.9},
            {"start": 2.0, "end": 4.0, "text": "Second segment", "confidence": 0.8}
        ]
        
        mock_model = Mock()
        mock_model.transcribe.return_value = {
            "segments": mock_segments,
            "duration": 4.0
        }
        
        transcription_service.model = mock_model
        
        # Test with progress callback
        progress_updates = []
        async def progress_callback(progress):
            progress_updates.append(progress)
            
        segments = await transcription_service.transcribe_video(
            "test.mp4",
            progress_callback=progress_callback
        )
        
        # Verify transcription
        assert len(segments) == 2
        assert segments[0].start_time == 0.0
        assert segments[0].end_time == 2.0
        assert segments[0].text == "First segment"
        assert segments[0].confidence == 0.9
        
        assert segments[1].start_time == 2.0
        assert segments[1].end_time == 4.0
        assert segments[1].text == "Second segment"
        assert segments[1].confidence == 0.8
        
        # Verify progress updates
        assert len(progress_updates) == 2
        assert progress_updates[0] == pytest.approx(50.0)  # 2.0/4.0 * 100
        assert progress_updates[1] == pytest.approx(100.0)  # 4.0/4.0 * 100
        
    @pytest.mark.asyncio
    async def test_transcribe_video_failure(self, transcription_service):
        """Test transcription failure handling."""
        mock_model = Mock()
        mock_model.transcribe.side_effect = Exception("Test error")
        transcription_service.model = mock_model
        
        with pytest.raises(ProcessingError, match="Failed to transcribe video"):
            await transcription_service.transcribe_video("test.mp4")
            
    @pytest.mark.asyncio
    async def test_transcribe_audio(self, transcription_service):
        """Test audio transcription (should use same method as video)."""
        mock_segments = [
            {"start": 0.0, "end": 1.0, "text": "Audio segment", "confidence": 0.9}
        ]
        
        mock_model = Mock()
        mock_model.transcribe.return_value = {
            "segments": mock_segments,
            "duration": 1.0
        }
        
        transcription_service.model = mock_model
        
        segments = await transcription_service.transcribe_audio("test.mp3")
        
        assert len(segments) == 1
        assert segments[0].text == "Audio segment"
        mock_model.transcribe.assert_called_once()
        
    def test_cleanup(self, transcription_service):
        """Test resource cleanup."""
        mock_model = Mock()
        transcription_service.model = mock_model
        
        transcription_service.cleanup()
        assert transcription_service.model is None 