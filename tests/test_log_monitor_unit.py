from unittest.mock import AsyncMock

import pytest

from src.log_monitor import LogMonitor


class DummyADB:
    def __init__(self):
        self.selected_device = "emulator-5554"

    async def execute_adb_command(
        self, command, timeout=30, capture_output=True, check_device=True
    ):
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

    res = await lm.get_logcat(
        tag_filter="MyApp", priority="I", max_lines=50, clear_first=True
    )
    assert res["success"] is True
    assert res["entries_count"] >= 1
    # Ensure parsed fields exist
    entry = res["entries"][0]
    assert "timestamp" in entry and "level" in entry and "tag" in entry

    # Search logs utility
    sres = await lm.search_logs(
        "wrong", tag_filter="MyApp", priority="V", max_results=10
    )
    assert sres["success"] is True
    assert sres["matches_found"] >= 1
