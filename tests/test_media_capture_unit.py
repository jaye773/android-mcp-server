import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock

from src.media_capture import MediaCapture


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

