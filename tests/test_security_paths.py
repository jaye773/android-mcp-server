"""Security tests for path-traversal and shell-injection fixes (T01)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

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

        result = await media.take_screenshot(filename="../evil.png")

        assert result["success"] is False
        assert "error" in result
        # Must happen before any ADB command is issued
        mock_adb_manager.execute_adb_command.assert_not_called()

    async def test_take_screenshot_rejects_absolute(self, mock_adb_manager, temp_dir):
        media = MediaCapture(mock_adb_manager, output_dir=str(temp_dir))

        result = await media.take_screenshot(filename="/tmp/x.png")

        assert result["success"] is False
        assert "error" in result
        mock_adb_manager.execute_adb_command.assert_not_called()


class TestStartRecordingPathSafety:
    """Video recording filename must reject traversal before ADB call."""

    async def test_start_recording_rejects_traversal(
        self, mock_adb_manager, temp_dir
    ):
        recorder = VideoRecorder(mock_adb_manager, output_dir=str(temp_dir))

        result = await recorder.start_recording(filename="../../etc/evil.mp4")

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

        result = await monitor.start_log_monitoring(output_file="../../etc/passwd")

        assert result["success"] is False
        assert "error" in result
        assert monitor.active_monitors == {}


class TestLogcatTagFilterShellSafe:
    """tag_filter passed to logcat must be shell-quoted."""

    async def test_logcat_tag_filter_shell_safe(self, mock_adb_manager, temp_dir):
        monitor = LogMonitor(mock_adb_manager, output_dir=str(temp_dir))

        malicious_tag = "Tag; rm -rf /"
        await monitor.get_logcat(tag_filter=malicious_tag, max_lines=10)

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

    async def test_start_log_monitoring_tag_filter_shell_safe(
        self, mock_adb_manager, temp_dir
    ):
        """tag_filter passed to start_log_monitoring must be shell-quoted.

        start_log_monitoring spawns a process via asyncio.create_subprocess_exec.
        A malicious tag_filter must be shlex.quote()'d before being interpolated
        into the logcat command, so that the argv list passed to the subprocess
        contains the safely-quoted value rather than an injection-capable one.
        """
        monitor = LogMonitor(mock_adb_manager, output_dir=str(temp_dir))

        malicious_tag = "evil; rm -rf /"

        mock_process = MagicMock()
        mock_process.pid = 4321
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()

        with patch(
            "asyncio.create_subprocess_exec", return_value=mock_process
        ) as mock_exec:
            result = await monitor.start_log_monitoring(tag_filter=malicious_tag)

        assert result["success"] is True
        mock_exec.assert_called_once()

        # Command list passed to subprocess (positional *cmd_parts)
        cmd_parts = list(mock_exec.call_args.args)

        # Clean up the background task created by start_log_monitoring
        info = monitor.active_monitors.get(result["monitor_id"])
        if info and info.get("task"):
            info["task"].cancel()

        # The tag itself must be present as a single shell-safe token.
        # shlex.split in log_monitor turns the quoted string back into one arg.
        assert malicious_tag in cmd_parts, (
            f"expected {malicious_tag!r} as a single argv token; "
            f"got cmd_parts={cmd_parts!r}"
        )

        # And the dangerous fragments must NOT appear as their own tokens,
        # which is what shell interpretation of an unquoted value would do.
        assert ";" not in cmd_parts
        assert "rm" not in cmd_parts
        assert "-rf" not in cmd_parts
        assert "/" not in cmd_parts
