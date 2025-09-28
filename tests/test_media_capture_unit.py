import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from src.media_capture import MediaCapture, VideoRecorder


class DummyADB:
    def __init__(self):
        self.selected_device = "emulator-5554"

    async def execute_adb_command(self, command, timeout=30, capture_output=True, check_device=True):
        # Simulate successful screencap and cleanup
        if "screencap" in command or "rm" in command:
            return {"success": True, "stdout": "", "stderr": "", "returncode": 0}
        return {"success": True, "stdout": "", "stderr": "", "returncode": 0}


@pytest.mark.asyncio
async def test_take_screenshot_without_pull(tmp_path: Path):
    adb = DummyADB()
    mc = MediaCapture(adb_manager=adb, output_dir=str(tmp_path))

    res = await mc.take_screenshot(filename="unit_test.png", pull_to_local=False)
    assert res["success"] is True
    assert res["action"] == "screenshot"
    assert res["device_path"].endswith("/unit_test.png")


@pytest.mark.asyncio
async def test_take_screenshot_with_pull(tmp_path: Path):
    adb = DummyADB()
    mc = MediaCapture(adb_manager=adb, output_dir=str(tmp_path))

    # Patch the pull method to simulate local file creation
    async def fake_pull(device_path: str, local_path: Path):
        local_path.write_bytes(b"data")
        return {
            "local_path": str(local_path),
            "file_size_bytes": 4,
            "file_size_mb": 0.0,
        }

    mc._pull_file_from_device = AsyncMock(side_effect=fake_pull)

    res = await mc.take_screenshot(filename="unit_test2.png", pull_to_local=True)
    assert res["success"] is True
    assert Path(res["local_path"]).exists()


@pytest.mark.asyncio
async def test_video_recording_lifecycle(monkeypatch, tmp_path: Path):
    adb = DummyADB()
    recorder = VideoRecorder(adb_manager=adb, output_dir=str(tmp_path))

    process = MagicMock()
    process.pid = 9876
    process.terminate = MagicMock()
    process.kill = MagicMock()
    process.communicate = AsyncMock(return_value=(b"", b""))

    monkeypatch.setattr(
        "src.media_capture.asyncio.create_subprocess_exec",
        AsyncMock(return_value=process),
    )
    monkeypatch.setattr("src.media_capture.asyncio.sleep", AsyncMock())
    recorder._pull_file_from_device = AsyncMock(
        return_value={
            "local_path": str(tmp_path / "sample.mp4"),
            "file_size_bytes": 10,
            "file_size_mb": 0.0,
        }
    )

    start_result = await recorder.start_recording(
        filename="sample.mp4", time_limit=5, bit_rate="2M", size_limit="720x1280", verbose=True
    )
    assert start_result["success"] is True
    recording_id = start_result["recording_id"]
    assert recording_id in recorder.active_recordings

    list_result = await recorder.list_active_recordings()
    assert list_result["count"] == 1
    assert list_result["active_recordings"][0]["recording_id"] == recording_id

    stop_result = await recorder.stop_recording(recording_id, pull_to_local=True)
    assert stop_result["success"] is True
    assert stop_result["local_path"].endswith("sample.mp4")
    process.terminate.assert_called_once()
    assert recording_id not in recorder.active_recordings


@pytest.mark.asyncio
async def test_stop_recording_missing_id(tmp_path: Path):
    adb = DummyADB()
    recorder = VideoRecorder(adb_manager=adb, output_dir=str(tmp_path))

    result = await recorder.stop_recording("missing")
    assert result["success"] is False
    assert "missing" in result["error"]

