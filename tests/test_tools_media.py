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
    async def test_happy_path(self, mock_media_capture, mock_adb_manager):
        ComponentRegistry.instance().register("media_capture", mock_media_capture)


        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
        params = ScreenshotParams(filename="test.png", pull_to_local=True)
        result = await take_screenshot(params)

        assert result["success"] is True
        mock_media_capture.take_screenshot.assert_awaited_once_with(
            filename="test.png", pull_to_local=True
        , device_id="emulator-5554")

    @pytest.mark.asyncio
    async def test_no_filename(self, mock_media_capture, mock_adb_manager):
        """Defaults (no filename) should work fine."""
        ComponentRegistry.instance().register("media_capture", mock_media_capture)

        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
        params = ScreenshotParams()
        result = await take_screenshot(params)

        assert result["success"] is True
        mock_media_capture.take_screenshot.assert_awaited_once_with(
            filename=None, pull_to_local=True
        , device_id="emulator-5554")

    @pytest.mark.asyncio
    async def test_path_traversal_filename(self, mock_media_capture, mock_adb_manager):
        """Path traversal in filename should be rejected."""
        ComponentRegistry.instance().register("media_capture", mock_media_capture)

        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
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
    async def test_exception(self, mock_media_capture, mock_adb_manager):
        ComponentRegistry.instance().register("media_capture", mock_media_capture)

        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
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
    async def test_happy_path(self, mock_video_recorder, mock_adb_manager):
        ComponentRegistry.instance().register("video_recorder", mock_video_recorder)


        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
        params = RecordingParams(filename="flow.mp4", time_limit=60)
        result = await start_screen_recording(params)

        assert result["success"] is True
        mock_video_recorder.start_recording.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_defaults(self, mock_video_recorder, mock_adb_manager):
        ComponentRegistry.instance().register("video_recorder", mock_video_recorder)


        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
        params = RecordingParams()
        result = await start_screen_recording(params)

        assert result["success"] is True
        mock_video_recorder.start_recording.assert_awaited_once_with(
            filename=None, time_limit=180, bit_rate=None, size_limit=None
        , device_id="emulator-5554")

    @pytest.mark.asyncio
    async def test_path_traversal_filename(self, mock_video_recorder, mock_adb_manager):
        ComponentRegistry.instance().register("video_recorder", mock_video_recorder)


        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
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
    async def test_exception(self, mock_video_recorder, mock_adb_manager):
        ComponentRegistry.instance().register("video_recorder", mock_video_recorder)

        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
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
    async def test_happy_path(self, mock_video_recorder, mock_adb_manager):
        ComponentRegistry.instance().register("video_recorder", mock_video_recorder)


        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
        params = StopRecordingParams(recording_id="rec_001", pull_to_local=True)
        result = await stop_screen_recording(params)

        assert result["success"] is True
        mock_video_recorder.stop_recording.assert_awaited_once_with(
            recording_id="rec_001", pull_to_local=True
        , device_id="emulator-5554")

    @pytest.mark.asyncio
    async def test_stop_all(self, mock_video_recorder, mock_adb_manager):
        """No recording_id -> stop all."""
        ComponentRegistry.instance().register("video_recorder", mock_video_recorder)

        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
        params = StopRecordingParams()
        result = await stop_screen_recording(params)

        assert result["success"] is True
        mock_video_recorder.stop_recording.assert_awaited_once_with(
            recording_id=None, pull_to_local=True
        , device_id="emulator-5554")

    @pytest.mark.asyncio
    async def test_identifier_validation_failure(self, mock_video_recorder, mock_adb_manager):
        """Shell metacharacters in recording_id should be rejected."""
        ComponentRegistry.instance().register("video_recorder", mock_video_recorder)

        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
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
    async def test_exception(self, mock_video_recorder, mock_adb_manager):
        ComponentRegistry.instance().register("video_recorder", mock_video_recorder)

        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
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
    async def test_happy_path(self, mock_video_recorder, mock_adb_manager):
        ComponentRegistry.instance().register("video_recorder", mock_video_recorder)


        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
        result = await list_active_recordings()

        assert result["success"] is True
        mock_video_recorder.list_active_recordings.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_missing_component(self):
        result = await list_active_recordings()

        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_exception(self, mock_video_recorder, mock_adb_manager):
        ComponentRegistry.instance().register("video_recorder", mock_video_recorder)

        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
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


# ---------------------------------------------------------------------------
# T10: Per-request device pinning — midflight-switch regressions
# ---------------------------------------------------------------------------


class _DeviceRecordingADB:
    """Minimal ADB stub that records the device_id used on every call.

    Emulates just enough of :class:`src.adb_manager.ADBManager` for the
    screenshot flow (screencap → pull → rm) to run end-to-end. Each call
    captures the device id it targets so tests can assert the whole
    operation pinned a single device even if ``selected_device`` changes.
    """

    def __init__(self, selected_device: str):
        self.selected_device = selected_device
        self.calls: list[tuple[str, str]] = []  # (command_kind, device_id)

    def default_device_id(self) -> str:
        if not self.selected_device:
            raise RuntimeError("no device selected")
        return self.selected_device

    async def execute_adb_command(
        self,
        command: str,
        *,
        device_id,
        timeout: int = 30,
        capture_output: bool = True,
        check_device: bool = True,
    ):
        if "screencap" in command:
            kind = "screencap"
        elif "pull" in command:
            kind = "pull"
        elif "shell rm" in command:
            kind = "rm"
        elif "uiautomator dump" in command:
            kind = "dump"
        elif "test -f" in command:
            kind = "test_f"
        elif "cat /sdcard" in command:
            kind = "cat"
        else:
            kind = "other"
        self.calls.append((kind, device_id))
        if kind == "pull":
            # Create the local destination so downstream Path.exists() is True
            import shlex as _shlex

            parts = _shlex.split(command)
            local_path = parts[-1]
            try:
                from pathlib import Path as _Path

                _Path(local_path).write_bytes(b"x")
            except Exception:
                pass
        if kind == "cat":
            return {
                "success": True,
                "stdout": "<hierarchy/>",
                "stderr": "",
                "returncode": 0,
            }
        if kind == "test_f":
            return {
                "success": True,
                "stdout": "exists",
                "stderr": "",
                "returncode": 0,
            }
        return {"success": True, "stdout": "", "stderr": "", "returncode": 0}


@pytest.mark.asyncio
async def test_device_switch_midflight_screenshot(tmp_path):
    """Switching selected_device after screencap must NOT divert the pull.

    Regression for T10: the screenshot flow is screencap → pull → rm. A
    client that mutates ``selected_device`` between the first adb call
    and the second must not cause the pull to target the new device.
    """
    from src.media_capture import MediaCapture

    adb = _DeviceRecordingADB(selected_device="device-A")
    media = MediaCapture(adb_manager=adb, output_dir=str(tmp_path))

    # Snapshot device id at the tool entry point (what the real tool does)
    pinned = adb.default_device_id()

    # Start the operation; midway, simulate a concurrent select_device(B)
    # by mutating the shared field BEFORE we call the next stage. We
    # simulate this by having a custom execute_adb_command that mutates
    # selected_device after the first (screencap) call.
    original_execute = adb.execute_adb_command
    first_seen = {"done": False}

    async def mutating_execute(command, *, device_id, **kwargs):
        result = await original_execute(command, device_id=device_id, **kwargs)
        if not first_seen["done"] and "screencap" in command:
            first_seen["done"] = True
            adb.selected_device = "device-B"
        return result

    adb.execute_adb_command = mutating_execute  # type: ignore[assignment]

    res = await media.take_screenshot(
        filename="midflight.png", pull_to_local=True, device_id=pinned
    )

    assert res["success"] is True
    # Every recorded adb call must have targeted device-A, including the
    # pull and the rm cleanup that run AFTER selected_device was mutated.
    assert adb.calls, "no adb calls were recorded"
    assert all(dev == "device-A" for _kind, dev in adb.calls), (
        f"expected all calls pinned to device-A, got {adb.calls!r}"
    )
    # And the mutation actually happened (sanity).
    assert adb.selected_device == "device-B"


@pytest.mark.asyncio
async def test_selected_device_snapshot_at_entry(tmp_path):
    """Mutating selected_device during an operation is not observed.

    Unit-level: once a tool entry snapshots ``default_device_id()`` and
    passes that through, subsequent adb calls in the same operation must
    use the snapshot, not re-read ``selected_device``.
    """
    from src.media_capture import MediaCapture

    adb = _DeviceRecordingADB(selected_device="device-X")
    media = MediaCapture(adb_manager=adb, output_dir=str(tmp_path))

    pinned = adb.default_device_id()

    # Mutate BEFORE any sub-call in the operation — the orchestrator must
    # still use the snapshot we captured at entry.
    adb.selected_device = "device-Y"

    res = await media.take_screenshot(
        filename="snapshot.png", pull_to_local=True, device_id=pinned
    )
    assert res["success"] is True
    assert all(dev == "device-X" for _kind, dev in adb.calls), (
        f"expected all calls pinned to device-X, got {adb.calls!r}"
    )
