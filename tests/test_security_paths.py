"""Security tests for path-traversal and shell-injection fixes (T01)."""

from __future__ import annotations

import pytest

from src.log_monitor import LogMonitor
from src.media_capture import MediaCapture, VideoRecorder
from src.path_safety import safe_join


class TestSafeJoin:
    """Unit tests for the path_safety.safe_join helper."""

    def test_accepts_plain_filename(self, temp_dir):
        result = safe_join(temp_dir, "photo.png")
        assert result == (temp_dir.resolve() / "photo.png")

    def test_rejects_absolute_path(self, temp_dir):
        with pytest.raises(ValueError):
            safe_join(temp_dir, "/tmp/x.png")

    def test_rejects_parent_traversal(self, temp_dir):
        with pytest.raises(ValueError):
            safe_join(temp_dir, "../evil.png")

    def test_rejects_nested_traversal(self, temp_dir):
        with pytest.raises(ValueError):
            safe_join(temp_dir, "sub/../../etc/passwd")

    def test_rejects_empty(self, temp_dir):
        with pytest.raises(ValueError):
            safe_join(temp_dir, "")


class TestTakeScreenshotPathSafety:
    """Screenshot filename must reject traversal/absolute paths before ADB call."""

    async def test_take_screenshot_rejects_traversal(self, mock_adb_manager, temp_dir):
        media = MediaCapture(mock_adb_manager, output_dir=str(temp_dir))

        result = await media.take_screenshot(filename="../evil.png", device_id="emulator-5554")

        assert result["success"] is False
        assert "error" in result
        # Must happen before any ADB command is issued
        mock_adb_manager.execute_adb_command.assert_not_called()

    async def test_take_screenshot_rejects_absolute(self, mock_adb_manager, temp_dir):
        media = MediaCapture(mock_adb_manager, output_dir=str(temp_dir))

        result = await media.take_screenshot(filename="/tmp/x.png", device_id="emulator-5554")

        assert result["success"] is False
        assert "error" in result
        mock_adb_manager.execute_adb_command.assert_not_called()


class TestStartRecordingPathSafety:
    """Video recording filename must reject traversal before ADB call."""

    async def test_start_recording_rejects_traversal(
        self, mock_adb_manager, temp_dir
    ):
        recorder = VideoRecorder(mock_adb_manager, output_dir=str(temp_dir))

        result = await recorder.start_recording(filename="../../etc/evil.mp4", device_id="emulator-5554")

        assert result["success"] is False
        assert "error" in result
        # No subprocess should have been spawned
        assert recorder.active_recordings == {}


class TestStartLogMonitoringPathSafety:
    """Log monitor output_file must reject traversal before ADB call."""

    async def test_start_log_monitoring_rejects_traversal(
        self, mock_adb_manager, temp_dir
    ):
        monitor = LogMonitor(mock_adb_manager, output_dir=str(temp_dir))

        result = await monitor.start_log_monitoring(output_file="../../etc/passwd", device_id="emulator-5554")

        assert result["success"] is False
        assert "error" in result
        assert monitor.active_monitors == {}


class TestLogcatTagFilterShellSafe:
    """tag_filter passed to logcat must be shell-quoted."""

    async def test_logcat_tag_filter_shell_safe(self, mock_adb_manager, temp_dir):
        monitor = LogMonitor(mock_adb_manager, output_dir=str(temp_dir))

        malicious_tag = "Tag; rm -rf /"
        await monitor.get_logcat(tag_filter=malicious_tag, max_lines=10, device_id="emulator-5554")

        # Collect all command strings passed to execute_adb_command
        call_args = [
            call.args[0] if call.args else call.kwargs.get("command", "")
            for call in mock_adb_manager.execute_adb_command.call_args_list
        ]
        logcat_calls = [c for c in call_args if "logcat" in c]
        assert logcat_calls, "expected at least one logcat invocation"

        # The malicious semicolon must not appear unquoted.
        # shlex.quote on this value produces a single-quoted string like
        #   'Tag; rm -rf /'
        # So the command string should contain the quoted form and not the
        # bare -s Tag;.
        joined = " ".join(logcat_calls)
        assert "'Tag; rm -rf /'" in joined
        assert "-s Tag;" not in joined
