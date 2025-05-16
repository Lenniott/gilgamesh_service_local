import os
import pytest
import numpy as np
from unittest.mock import Mock, patch, mock_open
from PIL import Image
import cv2
from app.services.scene_processing import SceneProcessingService
from app.core.errors import ProcessingError
from app.models.common import SceneCut, VideoMetadata

@pytest.fixture
def scene_service():
    """Create a scene processing service instance."""
    return SceneProcessingService(threshold=0.22)

@pytest.fixture
def mock_video_metadata():
    return VideoMetadata(
        source="test",
        title="Test Video",
        description="Test Description",
        tags=[],
        upload_date="20240101",
        duration=10.0,
        is_carousel=False
    )

@pytest.fixture
def mock_frame():
    """Create a mock video frame."""
    # Create a 100x100 frame with alternating black and white pixels
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    frame[::2, ::2] = [255, 255, 255]  # White pixels
    return frame

@pytest.fixture
def mock_different_frame():
    """Create a mock video frame that's different from the first one."""
    # Create a 100x100 frame with inverted pattern
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    frame[1::2, 1::2] = [255, 255, 255]  # White pixels in different positions
    return frame

class TestSceneProcessingService:
    @pytest.mark.asyncio
    async def test_process_video_empty(self, scene_service, mock_video_metadata, tmp_path):
        """Test processing an empty video file."""
        # Create an empty video file
        video_path = str(tmp_path / "empty.mp4")
        with open(video_path, 'wb') as f:
            f.write(b'')
            
        with patch('cv2.VideoCapture') as mock_cap:
            mock_cap.return_value.isOpened.return_value = False
            with pytest.raises(ProcessingError, match="Could not open video file"):
                await scene_service.process_video(video_path, mock_video_metadata)

    @pytest.mark.asyncio
    async def test_detect_scenes_single_scene(self, scene_service, mock_frame):
        """Test scene detection with a single scene."""
        with patch('cv2.VideoCapture') as mock_cap:
            # Mock video capture
            mock_cap_instance = Mock()
            mock_cap.return_value = mock_cap_instance
            mock_cap_instance.isOpened.return_value = True
            mock_cap_instance.get.side_effect = lambda prop: {
                cv2.CAP_PROP_FPS: 30.0,
                cv2.CAP_PROP_FRAME_COUNT: 100
            }.get(prop, 0)
            
            # Return same frame twice to simulate no scene change
            mock_cap_instance.read.side_effect = [(True, mock_frame), (True, mock_frame), (False, None)]
            
            scenes = scene_service._detect_scenes("test.mp4")
            assert len(scenes) == 1
            assert scenes[0].start_time == 0.0
            assert scenes[0].end_time == 2.0 / 30.0  # 2 frames at 30 fps
            assert scenes[0].confidence == 1.0  # Final scene gets full confidence

    @pytest.mark.asyncio
    async def test_detect_scenes_multiple_scenes(self, scene_service, mock_frame, mock_different_frame):
        """Test scene detection with multiple scenes."""
        with patch('cv2.VideoCapture') as mock_cap:
            # Mock video capture
            mock_cap_instance = Mock()
            mock_cap.return_value = mock_cap_instance
            mock_cap_instance.isOpened.return_value = True
            mock_cap_instance.get.side_effect = lambda prop: {
                cv2.CAP_PROP_FPS: 30.0,
                cv2.CAP_PROP_FRAME_COUNT: 100
            }.get(prop, 0)
            
            # Return different frames to simulate scene changes
            mock_cap_instance.read.side_effect = [
                (True, mock_frame),
                (True, mock_different_frame),  # Scene change (different frame)
                (True, mock_different_frame),
                (True, mock_frame),  # Scene change (back to original frame)
                (False, None)
            ]
            
            scenes = scene_service._detect_scenes("test.mp4")
            assert len(scenes) == 3  # Should detect all scene changes
            assert scenes[0].start_time == 0.0
            assert scenes[0].end_time == 1.0 / 30.0
            assert scenes[1].start_time == 1.0 / 30.0
            assert scenes[1].end_time == 3.0 / 30.0
            assert scenes[2].start_time == 3.0 / 30.0
            assert scenes[2].end_time == 4.0 / 30.0
            assert scenes[2].confidence == 1.0  # Final scene gets full confidence
            # Middle scene confidence should be based on frame difference
            assert 0.0 < scenes[1].confidence < 1.0

    @pytest.mark.asyncio
    async def test_extract_frame(self, scene_service, mock_frame, tmp_path):
        """Test frame extraction."""
        video_path = str(tmp_path / "test.mp4")
        timestamp = 1.0
        
        with patch('cv2.VideoCapture') as mock_cap:
            # Mock video capture
            mock_cap_instance = Mock()
            mock_cap.return_value = mock_cap_instance
            mock_cap_instance.isOpened.return_value = True
            mock_cap_instance.read.return_value = (True, mock_frame)
            
            frame_path = await scene_service._extract_frame(video_path, timestamp)
            
            # Verify frame was saved
            assert os.path.exists(frame_path)
            assert frame_path.endswith(f"frame_{int(timestamp)}.jpg")
            
            # Verify frame content
            saved_frame = cv2.imread(frame_path)
            assert saved_frame is not None
            assert saved_frame.shape == mock_frame.shape

    @pytest.mark.asyncio
    async def test_perform_ocr(self, scene_service, tmp_path):
        """Test OCR processing with a simple image."""
        # Create a test image with text
        image_path = str(tmp_path / "test_text.jpg")
        img = Image.new('RGB', (100, 100), color='white')
        img.save(image_path)
        
        with patch('pytesseract.image_to_string') as mock_ocr:
            mock_ocr.return_value = "Test Text"
            text = await scene_service._perform_ocr(image_path)
            assert text == "Test Text"
            
    @pytest.mark.asyncio
    async def test_perform_ocr_failure(self, scene_service):
        """Test OCR processing failure handling."""
        with patch('PIL.Image.open') as mock_open:
            mock_open.side_effect = Exception("Test error")
            text = await scene_service._perform_ocr("nonexistent.jpg")
            assert text == ""  # Should return empty string on failure

    @pytest.mark.asyncio
    async def test_process_video_integration(self, scene_service, mock_video_metadata, mock_frame, mock_different_frame, tmp_path):
        """Test the full process_video method with mocked components."""
        video_path = str(tmp_path / "test.mp4")
        
        # Create a frames directory
        frames_dir = tmp_path / "frames"
        frames_dir.mkdir(exist_ok=True)
        
        # Create a mock video capture that works for both scene detection and frame extraction
        mock_cap_instance = Mock()
        mock_cap_instance.isOpened.return_value = True
        mock_cap_instance.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FPS: 30.0,
            cv2.CAP_PROP_FRAME_COUNT: 100
        }.get(prop, 0)
        
        # For scene detection
        mock_cap_instance.read.side_effect = [
            (True, mock_frame),
            (True, mock_different_frame),  # Scene change
            (True, mock_frame),  # Scene change back
            (True, mock_different_frame),  # Scene change again
            (False, None)
        ]
        
        # For frame extraction
        def mock_read():
            # Return the appropriate frame based on the timestamp
            mock_cap_instance.get.side_effect = lambda prop: {
                cv2.CAP_PROP_POS_MSEC: 0  # This will be set by the code
            }.get(prop, 0)
            return True, mock_frame
        mock_cap_instance.read.side_effect = mock_read
        
        with patch('cv2.VideoCapture', return_value=mock_cap_instance), \
             patch('pytesseract.image_to_string') as mock_ocr, \
             patch('cv2.imwrite') as mock_imwrite, \
             patch('cv2.imread') as mock_imread:
            
            # Mock frame saving and reading
            def mock_save_frame(path, frame, *args, **kwargs):
                # Create the frame file
                with open(path, 'wb') as f:
                    f.write(b'mock frame data')
                return True
            mock_imwrite.side_effect = mock_save_frame
            mock_imread.return_value = mock_frame
            
            # Mock OCR
            mock_ocr.return_value = "Test Text"
            
            # Process video
            scenes = await scene_service.process_video(video_path, mock_video_metadata)
            
            # Verify results
            assert len(scenes) == 4  # Should detect all scene changes
            assert all(scene.onscreen_text == "Test Text" for scene in scenes)
            assert all(scene.confidence is not None for scene in scenes)
            assert scenes[-1].confidence == 1.0  # Final scene gets full confidence
            
            # Verify frame extraction was attempted for each scene
            assert mock_imwrite.call_count == 4  # One frame per scene
            assert mock_ocr.call_count == 4  # OCR performed on each frame 