"""Dedicated unit tests for src/tools/media.py.

Covers all 4 tool functions:
  - take_screenshot: happy path, filename validation, path traversal, missing component, exception
  - start_screen_recording: happy path, filename validation, missing component, exception
  - stop_screen_recording: happy path, identifier validation, missing component, exception
  - list_active_recordings: happy path, missing component, exception
  - register_media_tools wiring
"""

import pytest
from unittest.mock import MagicMock

from src.tools.media import (
    list_active_recordings,
    register_media_tools,
    start_screen_recording,
    stop_screen_recording,
    take_screenshot,
)
from src.tool_models import RecordingParams, ScreenshotParams, StopRecordingParams
from src.registry import ComponentRegistry


@pytest.fixture(autouse=True)
def _clean_registry():
    ComponentRegistry.reset()
    yield
    ComponentRegistry.reset()


# ---------------------------------------------------------------------------
# take_screenshot
# ---------------------------------------------------------------------------


class TestTakeScreenshot:
    @pytest.mark.asyncio
    async def test_happy_path(self, mock_media_capture):
        ComponentRegistry.instance().register("media_capture", mock_media_capture)

        params = ScreenshotParams(filename="test.png", pull_to_local=True)
        result = await take_screenshot(params)

        assert result["success"] is True
        mock_media_capture.take_screenshot.assert_awaited_once_with(
            filename="test.png", pull_to_local=True
        )

    @pytest.mark.asyncio
    async def test_no_filename(self, mock_media_capture):
        """Defaults (no filename) should work fine."""
        ComponentRegistry.instance().register("media_capture", mock_media_capture)

        params = ScreenshotParams()
        result = await take_screenshot(params)

        assert result["success"] is True
        mock_media_capture.take_screenshot.assert_awaited_once_with(
            filename=None, pull_to_local=True
        )

    @pytest.mark.asyncio
    async def test_path_traversal_filename(self, mock_media_capture):
        """Path traversal in filename should be rejected."""
        ComponentRegistry.instance().register("media_capture", mock_media_capture)

        params = ScreenshotParams(filename="../../etc/passwd")
        result = await take_screenshot(params)

        assert result["success"] is False
        assert "Validation failed" in result["error"]
        mock_media_capture.take_screenshot.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_component(self):
        params = ScreenshotParams()
        result = await take_screenshot(params)

        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_exception(self, mock_media_capture):
        ComponentRegistry.instance().register("media_capture", mock_media_capture)
        mock_media_capture.take_screenshot.side_effect = RuntimeError("screenshot fail")

        params = ScreenshotParams()
        result = await take_screenshot(params)

        assert result["success"] is False
        assert "screenshot fail" in result["error"]


# ---------------------------------------------------------------------------
# start_screen_recording
# ---------------------------------------------------------------------------


class TestStartScreenRecording:
    @pytest.mark.asyncio
    async def test_happy_path(self, mock_video_recorder):
        ComponentRegistry.instance().register("video_recorder", mock_video_recorder)

        params = RecordingParams(filename="flow.mp4", time_limit=60)
        result = await start_screen_recording(params)

        assert result["success"] is True
        mock_video_recorder.start_recording.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_defaults(self, mock_video_recorder):
        ComponentRegistry.instance().register("video_recorder", mock_video_recorder)

        params = RecordingParams()
        result = await start_screen_recording(params)

        assert result["success"] is True
        mock_video_recorder.start_recording.assert_awaited_once_with(
            filename=None, time_limit=180, bit_rate=None, size_limit=None
        )

    @pytest.mark.asyncio
    async def test_path_traversal_filename(self, mock_video_recorder):
        ComponentRegistry.instance().register("video_recorder", mock_video_recorder)

        params = RecordingParams(filename="../../../evil.mp4")
        result = await start_screen_recording(params)

        assert result["success"] is False
        assert "Validation failed" in result["error"]
        mock_video_recorder.start_recording.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_component(self):
        params = RecordingParams()
        result = await start_screen_recording(params)

        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_exception(self, mock_video_recorder):
        ComponentRegistry.instance().register("video_recorder", mock_video_recorder)
        mock_video_recorder.start_recording.side_effect = RuntimeError("recording fail")

        params = RecordingParams()
        result = await start_screen_recording(params)

        assert result["success"] is False
        assert "recording fail" in result["error"]


# ---------------------------------------------------------------------------
# stop_screen_recording
# ---------------------------------------------------------------------------


class TestStopScreenRecording:
    @pytest.mark.asyncio
    async def test_happy_path(self, mock_video_recorder):
        ComponentRegistry.instance().register("video_recorder", mock_video_recorder)

        params = StopRecordingParams(recording_id="rec_001", pull_to_local=True)
        result = await stop_screen_recording(params)

        assert result["success"] is True
        mock_video_recorder.stop_recording.assert_awaited_once_with(
            recording_id="rec_001", pull_to_local=True
        )

    @pytest.mark.asyncio
    async def test_stop_all(self, mock_video_recorder):
        """No recording_id -> stop all."""
        ComponentRegistry.instance().register("video_recorder", mock_video_recorder)

        params = StopRecordingParams()
        result = await stop_screen_recording(params)

        assert result["success"] is True
        mock_video_recorder.stop_recording.assert_awaited_once_with(
            recording_id=None, pull_to_local=True
        )

    @pytest.mark.asyncio
    async def test_identifier_validation_failure(self, mock_video_recorder):
        """Shell metacharacters in recording_id should be rejected."""
        ComponentRegistry.instance().register("video_recorder", mock_video_recorder)

        params = StopRecordingParams(recording_id="rec; rm -rf /")
        result = await stop_screen_recording(params)

        assert result["success"] is False
        assert "Validation failed" in result["error"]
        mock_video_recorder.stop_recording.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_component(self):
        params = StopRecordingParams()
        result = await stop_screen_recording(params)

        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_exception(self, mock_video_recorder):
        ComponentRegistry.instance().register("video_recorder", mock_video_recorder)
        mock_video_recorder.stop_recording.side_effect = RuntimeError("stop fail")

        params = StopRecordingParams(recording_id="rec_001")
        result = await stop_screen_recording(params)

        assert result["success"] is False
        assert "stop fail" in result["error"]


# ---------------------------------------------------------------------------
# list_active_recordings
# ---------------------------------------------------------------------------


class TestListActiveRecordings:
    @pytest.mark.asyncio
    async def test_happy_path(self, mock_video_recorder):
        ComponentRegistry.instance().register("video_recorder", mock_video_recorder)

        result = await list_active_recordings()

        assert result["success"] is True
        mock_video_recorder.list_active_recordings.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_missing_component(self):
        result = await list_active_recordings()

        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_exception(self, mock_video_recorder):
        ComponentRegistry.instance().register("video_recorder", mock_video_recorder)
        mock_video_recorder.list_active_recordings.side_effect = RuntimeError("list fail")

        result = await list_active_recordings()

        assert result["success"] is False
        assert "list fail" in result["error"]


# ---------------------------------------------------------------------------
# register_media_tools
# ---------------------------------------------------------------------------


class TestRegisterMediaTools:
    def test_registers_four_tools(self):
        mcp = MagicMock()
        mcp.tool.return_value = lambda fn: fn

        register_media_tools(mcp)

        assert mcp.tool.call_count == 4
