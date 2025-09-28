"""Extended tests for media_capture.py to improve code coverage.

This test suite focuses on covering the uncovered lines identified in the coverage report,
specifically targeting:
- Video recording lifecycle (start, stop, save)
- Screenshot with highlighting functionality
- Error scenarios and recovery paths
- Device interaction edge cases
- File management and cleanup
"""

import asyncio
import pytest
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any

from src.media_capture import MediaCapture, VideoRecorder, UIElement


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_adb_manager():
    """Mock ADB manager for media capture tests."""
    adb_mock = AsyncMock()
    adb_mock.selected_device = "emulator-5554"
    adb_mock.execute_adb_command.return_value = {
        "success": True,
        "stdout": "",
        "stderr": "",
        "returncode": 0,
    }
    return adb_mock


@pytest.fixture
def mock_ui_element():
    """Create a mock UI element for highlighting tests."""
    return UIElement(
        class_name="android.widget.Button",
        resource_id="com.test:id/button",
        text="Test Button",
        content_desc="Test button description",
        bounds={"left": 100, "top": 200, "right": 300, "bottom": 400},
        center={"x": 200, "y": 300},
        clickable=True,
        enabled=True,
        focusable=True,
        scrollable=False,
        displayed=True,
        children=[],
        xpath="//android.widget.Button[@resource-id='com.test:id/button']",
        index=0,
    )


class TestMediaCapture:
    """Test cases for MediaCapture class covering uncovered functionality."""

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_take_screenshot_auto_filename_generation(
        self, mock_adb_manager, temp_dir
    ):
        """Test automatic filename generation when none provided (lines 111-112)."""
        media_capture = MediaCapture(mock_adb_manager, str(temp_dir))

        result = await media_capture.take_screenshot(pull_to_local=False)

        assert result["success"] is True
        assert result["filename"].startswith("screenshot_")
        assert result["filename"].endswith(".png")
        assert len(result["filename"]) == len("screenshot_YYYYMMDD_HHMMSS.png")

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_take_screenshot_auto_extension_addition(
        self, mock_adb_manager, temp_dir
    ):
        """Test automatic extension addition when missing (line 116)."""
        media_capture = MediaCapture(mock_adb_manager, str(temp_dir))

        result = await media_capture.take_screenshot(
            filename="test_screenshot", format="jpg", pull_to_local=False
        )

        assert result["success"] is True
        assert result["filename"] == "test_screenshot.jpg"

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_take_screenshot_adb_command_failure(
        self, mock_adb_manager, temp_dir
    ):
        """Test screenshot failure when ADB command fails (line 126)."""
        media_capture = MediaCapture(mock_adb_manager, str(temp_dir))

        # Mock ADB command failure
        mock_adb_manager.execute_adb_command.return_value = {
            "success": False,
            "stderr": "Device not found",
        }

        result = await media_capture.take_screenshot()

        assert result["success"] is False
        assert result["error"] == "Screenshot capture failed"
        assert result["details"] == "Device not found"

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_take_screenshot_exception_handling(self, mock_adb_manager, temp_dir):
        """Test exception handling in screenshot operation (lines 151-153)."""
        media_capture = MediaCapture(mock_adb_manager, str(temp_dir))

        # Mock exception during execution
        mock_adb_manager.execute_adb_command.side_effect = Exception(
            "Connection timeout"
        )

        result = await media_capture.take_screenshot()

        assert result["success"] is False
        assert "Screenshot operation failed: Connection timeout" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_take_screenshot_with_highlights_base_failure(
        self, mock_adb_manager, temp_dir, mock_ui_element
    ):
        """Test screenshot with highlights when base screenshot fails (lines 159-227)."""
        media_capture = MediaCapture(mock_adb_manager, str(temp_dir))

        # Mock base screenshot failure
        mock_adb_manager.execute_adb_command.return_value = {
            "success": False,
            "stderr": "Screencap failed",
        }

        result = await media_capture.take_screenshot_with_highlights([mock_ui_element])

        assert result["success"] is False
        assert result["error"] == "Screenshot capture failed"

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_take_screenshot_with_highlights_calls_base_screenshot(
        self, mock_adb_manager, temp_dir, mock_ui_element
    ):
        """Test screenshot with highlights calls base screenshot method (lines 159-164)."""
        media_capture = MediaCapture(mock_adb_manager, str(temp_dir))

        # Mock the take_screenshot method to return a successful result
        media_capture.take_screenshot = AsyncMock(
            return_value={
                "success": True,
                "local_path": str(temp_dir / "test.png"),
                "filename": "test.png",
            }
        )

        result = await media_capture.take_screenshot_with_highlights([mock_ui_element])

        # Verify take_screenshot was called with correct parameters
        media_capture.take_screenshot.assert_called_once_with(None, pull_to_local=True)
        assert result["success"] is True

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_take_screenshot_with_highlights_exception(
        self, mock_adb_manager, temp_dir, mock_ui_element
    ):
        """Test exception handling in screenshot with highlights (lines 225-230)."""
        media_capture = MediaCapture(mock_adb_manager, str(temp_dir))

        # Mock exception during operation
        media_capture.take_screenshot = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        result = await media_capture.take_screenshot_with_highlights([mock_ui_element])

        assert result["success"] is False
        assert "Screenshot with highlights failed: Unexpected error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_pull_file_from_device_success(self, mock_adb_manager, temp_dir):
        """Test successful file pull from device (lines 236-246)."""
        media_capture = MediaCapture(mock_adb_manager, str(temp_dir))

        # Create test file
        test_file = temp_dir / "test_file.png"
        test_file.write_bytes(b"test file content")

        # Mock successful pull
        mock_adb_manager.execute_adb_command.return_value = {
            "success": True,
            "stdout": "pull success",
        }

        result = await media_capture._pull_file_from_device(
            "/sdcard/test.png", test_file
        )

        assert "local_path" in result
        assert result["file_size_bytes"] == 17  # Length of "test file content"
        assert result["file_size_mb"] == 0.0

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_pull_file_from_device_failure(self, mock_adb_manager, temp_dir):
        """Test failed file pull from device (lines 247-251)."""
        media_capture = MediaCapture(mock_adb_manager, str(temp_dir))

        test_file = temp_dir / "nonexistent_file.png"

        # Mock failed pull
        mock_adb_manager.execute_adb_command.return_value = {
            "success": False,
            "stderr": "File not found on device",
        }

        result = await media_capture._pull_file_from_device(
            "/sdcard/test.png", test_file
        )

        assert result["pull_failed"] is True
        assert result["pull_error"] == "File not found on device"

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_pull_file_from_device_exception(self, mock_adb_manager, temp_dir):
        """Test exception handling in file pull (lines 253-257)."""
        media_capture = MediaCapture(mock_adb_manager, str(temp_dir))

        test_file = temp_dir / "test_file.png"

        # Mock exception during pull
        mock_adb_manager.execute_adb_command.side_effect = Exception("Network error")

        result = await media_capture._pull_file_from_device(
            "/sdcard/test.png", test_file
        )

        assert result["pull_failed"] is True
        assert "Pull operation failed: Network error" in result["pull_error"]


class TestVideoRecorder:
    """Test cases for VideoRecorder class covering uncovered functionality."""

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_video_recorder_init(self, mock_adb_manager, temp_dir):
        """Test VideoRecorder initialization (lines 264-267)."""
        recorder = VideoRecorder(mock_adb_manager, str(temp_dir))

        assert recorder.adb_manager == mock_adb_manager
        assert recorder.output_dir == Path(temp_dir)
        assert recorder.active_recordings == {}
        assert recorder.output_dir.exists()

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_start_recording_auto_filename(self, mock_adb_manager, temp_dir):
        """Test start recording with auto-generated filename (lines 287-355)."""
        recorder = VideoRecorder(mock_adb_manager, str(temp_dir))

        # Mock subprocess creation
        mock_process = AsyncMock()
        mock_process.pid = 12345

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await recorder.start_recording()

            assert result["success"] is True
            assert result["action"] == "start_recording"
            assert result["filename"].startswith("recording_")
            assert result["filename"].endswith(".mp4")
            assert result["process_id"] == 12345
            assert result["time_limit"] == 180

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_start_recording_custom_filename_without_extension(
        self, mock_adb_manager, temp_dir
    ):
        """Test start recording with custom filename without extension (lines 294-295)."""
        recorder = VideoRecorder(mock_adb_manager, str(temp_dir))

        mock_process = AsyncMock()
        mock_process.pid = 12345

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await recorder.start_recording(filename="custom_recording")

            assert result["success"] is True
            assert result["filename"] == "custom_recording.mp4"

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_start_recording_with_all_options(self, mock_adb_manager, temp_dir):
        """Test start recording with all options specified (lines 300-314)."""
        recorder = VideoRecorder(mock_adb_manager, str(temp_dir))

        mock_process = AsyncMock()
        mock_process.pid = 12345

        with patch(
            "asyncio.create_subprocess_exec", return_value=mock_process
        ) as mock_exec:
            result = await recorder.start_recording(
                filename="test_recording.mp4",
                time_limit=60,
                bit_rate="8M",
                size_limit="1280x720",
                verbose=True,
            )

            assert result["success"] is True
            assert result["bit_rate"] == "8M"
            assert result["size_limit"] == "1280x720"
            assert result["time_limit"] == 60

            # Verify command was built correctly
            mock_exec.assert_called_once()
            args = mock_exec.call_args[0]
            cmd_str = " ".join(args)
            assert "--bit-rate 8M" in cmd_str
            assert "--size 1280x720" in cmd_str
            assert "--verbose" in cmd_str
            assert "--time-limit 60" in cmd_str

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_start_recording_exception(self, mock_adb_manager, temp_dir):
        """Test start recording exception handling (lines 353-355)."""
        recorder = VideoRecorder(mock_adb_manager, str(temp_dir))

        # Mock subprocess creation failure
        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=Exception("Process creation failed"),
        ):
            result = await recorder.start_recording()

            assert result["success"] is False
            assert (
                "Failed to start recording: Process creation failed" in result["error"]
            )

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_stop_recording_all_active(self, mock_adb_manager, temp_dir):
        """Test stopping all active recordings (lines 367-380)."""
        recorder = VideoRecorder(mock_adb_manager, str(temp_dir))

        # Add some mock active recordings
        mock_process1 = AsyncMock()
        mock_process2 = AsyncMock()

        recorder.active_recordings = {
            "rec1": {
                "process": mock_process1,
                "filename": "rec1.mp4",
                "device_path": "/sdcard/rec1.mp4",
                "local_path": temp_dir / "rec1.mp4",
                "start_time": datetime.now(),
                "time_limit": 180,
                "options": "",
            },
            "rec2": {
                "process": mock_process2,
                "filename": "rec2.mp4",
                "device_path": "/sdcard/rec2.mp4",
                "local_path": temp_dir / "rec2.mp4",
                "start_time": datetime.now(),
                "time_limit": 180,
                "options": "",
            },
        }

        # Mock successful stop for each recording
        async def mock_stop_single(recording_id, pull_to_local):
            return {
                "success": True,
                "recording_id": recording_id,
                "filename": f"{recording_id}.mp4",
            }

        recorder._stop_single_recording = AsyncMock(side_effect=mock_stop_single)

        result = await recorder.stop_recording(recording_id=None)

        assert result["success"] is True
        assert result["action"] == "stop_all_recordings"
        assert result["recordings_stopped"] == 2
        assert len(result["results"]) == 2

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_stop_recording_specific(self, mock_adb_manager, temp_dir):
        """Test stopping specific recording (lines 381-383)."""
        recorder = VideoRecorder(mock_adb_manager, str(temp_dir))

        # Mock specific recording stop
        async def mock_stop_single(recording_id, pull_to_local):
            return {
                "success": True,
                "recording_id": recording_id,
                "filename": "specific.mp4",
            }

        recorder._stop_single_recording = AsyncMock(side_effect=mock_stop_single)

        result = await recorder.stop_recording(recording_id="specific_rec")

        assert result["success"] is True
        assert result["recording_id"] == "specific_rec"

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_stop_recording_exception(self, mock_adb_manager, temp_dir):
        """Test stop recording exception handling (lines 385-387)."""
        recorder = VideoRecorder(mock_adb_manager, str(temp_dir))

        recorder._stop_single_recording = AsyncMock(
            side_effect=Exception("Stop failed")
        )

        result = await recorder.stop_recording(recording_id="test_rec")

        assert result["success"] is False
        assert "Failed to stop recording: Stop failed" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_stop_single_recording_not_found(self, mock_adb_manager, temp_dir):
        """Test stopping recording that doesn't exist (lines 393-398)."""
        recorder = VideoRecorder(mock_adb_manager, str(temp_dir))

        result = await recorder._stop_single_recording("nonexistent_rec", True)

        assert result["success"] is False
        assert "Recording nonexistent_rec not found" in result["error"]
        assert result["active_recordings"] == []

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_stop_single_recording_success_with_pull(
        self, mock_adb_manager, temp_dir
    ):
        """Test successful single recording stop with file pull (lines 400-441)."""
        recorder = VideoRecorder(mock_adb_manager, str(temp_dir))

        # Create mock process
        mock_process = Mock()
        mock_process.terminate = Mock()
        mock_process.communicate = AsyncMock(return_value=(b"stdout", b"stderr"))

        # Add active recording
        start_time = datetime.now()
        recording_info = {
            "process": mock_process,
            "filename": "test.mp4",
            "device_path": "/sdcard/test.mp4",
            "local_path": temp_dir / "test.mp4",
            "start_time": start_time,
            "time_limit": 180,
            "options": "",
        }
        recorder.active_recordings["test_rec"] = recording_info

        # Mock successful file pull
        async def mock_pull_file(device_path, local_path):
            local_path.write_bytes(b"video data")
            return {
                "local_path": str(local_path),
                "file_size_bytes": 10,
                "file_size_mb": 0.0,
            }

        recorder._pull_file_from_device = AsyncMock(side_effect=mock_pull_file)

        result = await recorder._stop_single_recording("test_rec", True)

        assert result["success"] is True
        assert result["action"] == "stop_recording"
        assert result["recording_id"] == "test_rec"
        assert result["filename"] == "test.mp4"
        assert "duration_seconds" in result
        assert "test_rec" not in recorder.active_recordings

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_stop_single_recording_timeout(self, mock_adb_manager, temp_dir):
        """Test single recording stop timeout (lines 443-452)."""
        recorder = VideoRecorder(mock_adb_manager, str(temp_dir))

        # Create mock process that times out
        mock_process = Mock()
        mock_process.kill = Mock()
        mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())

        # Add active recording
        recording_info = {
            "process": mock_process,
            "filename": "test.mp4",
            "device_path": "/sdcard/test.mp4",
            "local_path": temp_dir / "test.mp4",
            "start_time": datetime.now(),
            "time_limit": 180,
            "options": "",
        }
        recorder.active_recordings["test_rec"] = recording_info

        result = await recorder._stop_single_recording("test_rec", True)

        assert result["success"] is False
        assert "Recording stop timed out - force killed" in result["error"]
        assert result["recording_id"] == "test_rec"
        assert "test_rec" not in recorder.active_recordings
        mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_stop_single_recording_exception(self, mock_adb_manager, temp_dir):
        """Test single recording stop exception handling (lines 453-458)."""
        recorder = VideoRecorder(mock_adb_manager, str(temp_dir))

        # Create mock process that raises exception
        mock_process = Mock()
        mock_process.communicate = AsyncMock(
            side_effect=Exception("Communication error")
        )

        # Add active recording
        recording_info = {
            "process": mock_process,
            "filename": "test.mp4",
            "device_path": "/sdcard/test.mp4",
            "local_path": temp_dir / "test.mp4",
            "start_time": datetime.now(),
            "time_limit": 180,
            "options": "",
        }
        recorder.active_recordings["test_rec"] = recording_info

        result = await recorder._stop_single_recording("test_rec", True)

        assert result["success"] is False
        assert (
            "Failed to stop recording test_rec: Communication error" in result["error"]
        )

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_pull_file_from_device_success_video(
        self, mock_adb_manager, temp_dir
    ):
        """Test successful video file pull from device (lines 464-474)."""
        recorder = VideoRecorder(mock_adb_manager, str(temp_dir))

        # Create test video file
        test_file = temp_dir / "test_video.mp4"
        test_file.write_bytes(b"video file content")

        # Mock successful pull
        mock_adb_manager.execute_adb_command.return_value = {
            "success": True,
            "stdout": "pull success",
        }

        result = await recorder._pull_file_from_device("/sdcard/test.mp4", test_file)

        assert "local_path" in result
        assert result["file_size_bytes"] == 18  # Length of "video file content"
        assert result["file_size_mb"] == 0.0

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_pull_file_from_device_failure_video(
        self, mock_adb_manager, temp_dir
    ):
        """Test failed video file pull from device (lines 475-479)."""
        recorder = VideoRecorder(mock_adb_manager, str(temp_dir))

        test_file = temp_dir / "nonexistent_video.mp4"

        # Mock failed pull
        mock_adb_manager.execute_adb_command.return_value = {
            "success": False,
            "stderr": "Video file not found",
        }

        result = await recorder._pull_file_from_device("/sdcard/test.mp4", test_file)

        assert result["pull_failed"] is True
        assert result["pull_error"] == "Video file not found"

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_pull_file_from_device_exception_video(
        self, mock_adb_manager, temp_dir
    ):
        """Test exception handling in video file pull (lines 481-485)."""
        recorder = VideoRecorder(mock_adb_manager, str(temp_dir))

        test_file = temp_dir / "test_video.mp4"

        # Mock exception during pull
        mock_adb_manager.execute_adb_command.side_effect = Exception("Storage error")

        result = await recorder._pull_file_from_device("/sdcard/test.mp4", test_file)

        assert result["pull_failed"] is True
        assert "Pull operation failed: Storage error" in result["pull_error"]

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_list_active_recordings_success(self, mock_adb_manager, temp_dir):
        """Test listing active recordings (lines 491-505)."""
        recorder = VideoRecorder(mock_adb_manager, str(temp_dir))

        # Add some active recordings
        start_time = datetime.now()
        recorder.active_recordings = {
            "rec1": {
                "process": AsyncMock(),
                "filename": "rec1.mp4",
                "device_path": "/sdcard/rec1.mp4",
                "local_path": temp_dir / "rec1.mp4",
                "start_time": start_time,
                "time_limit": 180,
                "options": "",
            },
            "rec2": {
                "process": AsyncMock(),
                "filename": "rec2.mp4",
                "device_path": "/sdcard/rec2.mp4",
                "local_path": temp_dir / "rec2.mp4",
                "start_time": start_time,
                "time_limit": 60,
                "options": "",
            },
        }

        result = await recorder.list_active_recordings()

        assert result["success"] is True
        assert result["count"] == 2
        assert len(result["active_recordings"]) == 2

        # Check first recording info
        rec1_info = result["active_recordings"][0]
        assert rec1_info["recording_id"] == "rec1"
        assert rec1_info["filename"] == "rec1.mp4"
        assert rec1_info["time_limit"] == 180
        assert "duration_seconds" in rec1_info

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_list_active_recordings_exception(self, mock_adb_manager, temp_dir):
        """Test list active recordings exception handling (lines 507-509)."""
        recorder = VideoRecorder(mock_adb_manager, str(temp_dir))

        # Mock exception during listing
        recorder.active_recordings = Mock()
        recorder.active_recordings.items.side_effect = Exception("Dictionary error")

        result = await recorder.list_active_recordings()

        assert result["success"] is False
        assert "Failed to list recordings: Dictionary error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_cleanup_all_recordings_success(self, mock_adb_manager, temp_dir):
        """Test successful cleanup of all recordings (lines 513-557)."""
        recorder = VideoRecorder(mock_adb_manager, str(temp_dir))

        # Add some active recordings
        mock_process1 = Mock()
        mock_process1.kill = Mock()
        mock_process2 = Mock()
        mock_process2.kill = Mock()

        recorder.active_recordings = {
            "rec1": {
                "process": mock_process1,
                "filename": "rec1.mp4",
                "device_path": "/sdcard/rec1.mp4",
                "local_path": temp_dir / "rec1.mp4",
                "start_time": datetime.now(),
                "time_limit": 180,
                "options": "",
            },
            "rec2": {
                "process": mock_process2,
                "filename": "rec2.mp4",
                "device_path": "/sdcard/rec2.mp4",
                "local_path": temp_dir / "rec2.mp4",
                "start_time": datetime.now(),
                "time_limit": 180,
                "options": "",
            },
        }

        # Mock successful cleanup commands
        mock_adb_manager.execute_adb_command.return_value = {
            "success": True,
            "stderr": "File removed",
        }

        result = await recorder.cleanup_all_recordings()

        assert result["success"] is True
        assert result["action"] == "cleanup_all"
        assert result["cleaned_count"] == 2
        assert len(result["results"]) == 2
        assert recorder.active_recordings == {}

        # Verify processes were killed
        mock_process1.kill.assert_called_once()
        mock_process2.kill.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_cleanup_all_recordings_partial_failure(
        self, mock_adb_manager, temp_dir
    ):
        """Test cleanup with some failures (lines 540-547)."""
        recorder = VideoRecorder(mock_adb_manager, str(temp_dir))

        # Mock process that raises exception
        mock_process = Mock()
        mock_process.kill = Mock(side_effect=Exception("Process kill failed"))

        recorder.active_recordings = {
            "rec1": {
                "process": mock_process,
                "filename": "rec1.mp4",
                "device_path": "/sdcard/rec1.mp4",
                "local_path": temp_dir / "rec1.mp4",
                "start_time": datetime.now(),
                "time_limit": 180,
                "options": "",
            }
        }

        result = await recorder.cleanup_all_recordings()

        assert result["success"] is True
        assert result["cleaned_count"] == 1
        assert result["results"][0]["cleaned"] is False
        assert "Process kill failed" in result["results"][0]["error"]
        assert recorder.active_recordings == {}

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_cleanup_all_recordings_exception(self, mock_adb_manager, temp_dir):
        """Test cleanup exception handling (lines 559-561)."""
        recorder = VideoRecorder(mock_adb_manager, str(temp_dir))

        # Mock exception during cleanup
        recorder.active_recordings = Mock()
        recorder.active_recordings.keys.side_effect = Exception("Keys error")

        result = await recorder.cleanup_all_recordings()

        assert result["success"] is False
        assert "Cleanup failed: Keys error" in result["error"]


class TestMediaCaptureIntegration:
    """Integration tests for media capture functionality."""

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_screenshot_and_video_workflow(
        self, mock_adb_manager, temp_dir, mock_ui_element
    ):
        """Test complete workflow of screenshot and video operations."""
        media_capture = MediaCapture(mock_adb_manager, str(temp_dir))
        video_recorder = VideoRecorder(mock_adb_manager, str(temp_dir))

        # Mock file creation for pull operations
        async def mock_pull_file(device_path, local_path):
            local_path.write_bytes(b"media content")
            return {
                "local_path": str(local_path),
                "file_size_bytes": 13,
                "file_size_mb": 0.0,
            }

        media_capture._pull_file_from_device = AsyncMock(side_effect=mock_pull_file)
        video_recorder._pull_file_from_device = AsyncMock(side_effect=mock_pull_file)

        # Mock subprocess for video recording
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.communicate.return_value = (b"", b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            # Start recording
            start_result = await video_recorder.start_recording(
                filename="workflow_test"
            )
            assert start_result["success"] is True

            # Take screenshot during recording
            screenshot_result = await media_capture.take_screenshot(
                filename="workflow_screenshot"
            )
            assert screenshot_result["success"] is True

            # Take screenshot with highlights
            highlight_result = await media_capture.take_screenshot_with_highlights(
                [mock_ui_element], filename="workflow_highlighted"
            )
            assert highlight_result["success"] is True

            # Stop recording
            stop_result = await video_recorder.stop_recording(
                start_result["recording_id"]
            )
            assert stop_result["success"] is True

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_error_recovery_scenarios(self, mock_adb_manager, temp_dir):
        """Test various error recovery scenarios."""
        media_capture = MediaCapture(mock_adb_manager, str(temp_dir))
        video_recorder = VideoRecorder(mock_adb_manager, str(temp_dir))

        # Test screenshot failure recovery
        mock_adb_manager.execute_adb_command.return_value = {
            "success": False,
            "stderr": "Device not responding",
        }

        screenshot_result = await media_capture.take_screenshot()
        assert screenshot_result["success"] is False
        assert "Screenshot capture failed" in screenshot_result["error"]

        # Test video recording failure recovery
        with patch(
            "asyncio.create_subprocess_exec", side_effect=OSError("Command not found")
        ):
            recording_result = await video_recorder.start_recording()
            assert recording_result["success"] is False
            assert "Failed to start recording" in recording_result["error"]

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_resource_cleanup_on_errors(self, mock_adb_manager, temp_dir):
        """Test proper resource cleanup when errors occur."""
        video_recorder = VideoRecorder(mock_adb_manager, str(temp_dir))

        # Add recording that will fail during stop
        mock_process = Mock()
        mock_process.communicate = AsyncMock(side_effect=Exception("Process error"))

        recording_info = {
            "process": mock_process,
            "filename": "test.mp4",
            "device_path": "/sdcard/test.mp4",
            "local_path": temp_dir / "test.mp4",
            "start_time": datetime.now(),
            "time_limit": 180,
            "options": "",
        }
        video_recorder.active_recordings["error_rec"] = recording_info

        # Attempt to stop should handle error gracefully
        result = await video_recorder._stop_single_recording("error_rec", True)
        assert result["success"] is False

        # But should still clean up the recording from active list
        # (This tests the error handling doesn't leave orphaned recordings)
        assert "error_rec" not in video_recorder.active_recordings

    @pytest.mark.asyncio
    @pytest.mark.media
    async def test_concurrent_operations(self, mock_adb_manager, temp_dir):
        """Test handling of concurrent media operations."""
        media_capture = MediaCapture(mock_adb_manager, str(temp_dir))
        video_recorder = VideoRecorder(mock_adb_manager, str(temp_dir))

        # Mock file creation
        async def mock_pull_file(device_path, local_path):
            await asyncio.sleep(0.1)  # Simulate some delay
            local_path.write_bytes(b"concurrent content")
            return {
                "local_path": str(local_path),
                "file_size_bytes": 18,
                "file_size_mb": 0.0,
            }

        media_capture._pull_file_from_device = AsyncMock(side_effect=mock_pull_file)

        # Execute multiple screenshots concurrently
        tasks = [
            media_capture.take_screenshot(filename=f"concurrent_{i}") for i in range(3)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        for i, result in enumerate(results):
            assert not isinstance(result, Exception)
            assert result["success"] is True
            assert result["filename"] == f"concurrent_{i}.png"
