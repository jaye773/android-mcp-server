import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.log_monitor import LogMonitor


class DummyADB:
    def __init__(self):
        self.selected_device = "emulator-5554"

    async def execute_adb_command(self, command, timeout=30, capture_output=True, check_device=True):
        # Simulate logcat output with two lines
        if "logcat" in command and "-d" in command:
            return {
                "success": True,
                "stdout": (
                    "01-01 12:00:00.000  123  456 I MyApp: Started\n"
                    "01-01 12:00:00.010  123  456 E MyApp: Something went wrong\n"
                ),
                "stderr": "",
                "returncode": 0,
            }
        if "logcat -c" in command:
            return {"success": True, "stdout": "", "stderr": "", "returncode": 0}
        return {"success": True, "stdout": "", "stderr": "", "returncode": 0}


@pytest.mark.asyncio
async def test_get_logcat_parsing_and_filters():
    adb = DummyADB()
    lm = LogMonitor(adb_manager=adb)

    res = await lm.get_logcat(tag_filter="MyApp", priority="I", max_lines=50, clear_first=True)
    assert res["success"] is True
    assert res["entries_count"] >= 1
    # Ensure parsed fields exist
    entry = res["entries"][0]
    assert "timestamp" in entry and "level" in entry and "tag" in entry

    # Search logs utility
    sres = await lm.search_logs("wrong", tag_filter="MyApp", priority="V", max_results=10)
    assert sres["success"] is True
    assert sres["matches_found"] >= 1


@pytest.mark.asyncio
async def test_log_monitor_start_stop_lifecycle(monkeypatch, tmp_path):
    adb = DummyADB()
    monitor = LogMonitor(adb_manager=adb, output_dir=str(tmp_path))

    process = MagicMock()
    process.pid = 4321
    process.terminate = MagicMock()

    monkeypatch.setattr(
        "src.log_monitor.asyncio.create_subprocess_exec",
        AsyncMock(return_value=process),
    )

    original_create_task = asyncio.create_task
    monkeypatch.setattr(
        "src.log_monitor.asyncio.create_task",
        lambda coro: original_create_task(asyncio.sleep(0)),
    )
    monkeypatch.setattr(LogMonitor, "_monitor_logs", AsyncMock(return_value=None))

    start_result = await monitor.start_log_monitoring(
        tag_filter="MyApp", priority="W", output_file="session"
    )
    assert start_result["success"] is True
    monitor_id = start_result["monitor_id"]
    assert monitor_id in monitor.active_monitors

    list_result = await monitor.list_active_monitors()
    assert list_result["count"] == 1
    assert list_result["active_monitors"][0]["monitor_id"] == monitor_id

    stop_result = await monitor.stop_log_monitoring(monitor_id)
    assert stop_result["success"] is True
    assert monitor_id not in monitor.active_monitors
    process.terminate.assert_called_once()

