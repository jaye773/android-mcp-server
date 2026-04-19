import asyncio
import shlex
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.media_capture import MediaCapture


class DummyADB:
    def __init__(self):
        self.selected_device = "emulator-5554"

    async def execute_adb_command(
        self,
        command,
        *,
        device_id=None,
        timeout=30,
        capture_output=True,
        check_device=True,
    ):
        # Simulate successful screencap and cleanup
        if "screencap" in command or "rm" in command:
            return {"success": True, "stdout": "", "stderr": "", "returncode": 0}
        return {"success": True, "stdout": "", "stderr": "", "returncode": 0}


@pytest.mark.asyncio
async def test_take_screenshot_without_pull(tmp_path: Path):
    adb = DummyADB()
    mc = MediaCapture(adb_manager=adb, output_dir=str(tmp_path))

    res = await mc.take_screenshot(filename="unit_test.png", pull_to_local=False, device_id="emulator-5554")
    assert res["success"] is True
    assert res["action"] == "screenshot"
    assert res["device_path"].endswith("/unit_test.png")


@pytest.mark.asyncio
async def test_take_screenshot_with_pull(tmp_path: Path):
    adb = DummyADB()
    mc = MediaCapture(adb_manager=adb, output_dir=str(tmp_path))

    # Patch the module-level pull function to simulate local file creation
    async def fake_pull(adb_manager, device_path: str, local_path: Path, *, device_id):
        local_path.write_bytes(b"data")
        return {
            "local_path": str(local_path),
            "file_size_bytes": 4,
            "file_size_mb": 0.0,
        }

    with patch("src.media_capture._pull_file_from_device", side_effect=fake_pull):
        res = await mc.take_screenshot(filename="unit_test2.png", pull_to_local=True, device_id="emulator-5554")
    assert res["success"] is True
    assert Path(res["local_path"]).exists()


class RecordingADB:
    """ADB stub that records every command string passed to execute_adb_command."""

    def __init__(self):
        self.selected_device = "emulator-5554"
        self.commands: list[str] = []

    async def execute_adb_command(
        self,
        command,
        *,
        device_id=None,
        timeout=30,
        capture_output=True,
        check_device=True,
    ):
        self.commands.append(command)
        return {"success": True, "stdout": "", "stderr": "", "returncode": 0}

    async def spawn_adb_process(
        self,
        cmd_template,
        *,
        device_id=None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=None,
    ):
        """Record the command and delegate to create_subprocess_exec (for patches)."""
        device = device_id or self.selected_device
        self.commands.append(cmd_template.format(device=device))
        args = shlex.split(cmd_template.format(device=device))
        return await asyncio.create_subprocess_exec(
            *args, stdout=stdout, stderr=stderr, stdin=stdin
        )


@pytest.mark.asyncio
async def test_media_capture_filename_with_spaces_quoted(tmp_path: Path):
    """Filenames with spaces must be shlex-quoted in adb shell command strings.

    Covers screencap, cleanup rm (screenshot), and screenrecord command strings.
    """
    adb = RecordingADB()
    mc = MediaCapture(adb_manager=adb, output_dir=str(tmp_path))

    spaced_name = "my shot.png"
    expected_device_path = f"/sdcard/{spaced_name}"
    quoted_device_path = shlex.quote(expected_device_path)

    # Patch pull to no-op so cleanup rm still runs.
    async def fake_pull(adb_manager, device_path, local_path, *, device_id):
        Path(local_path).write_bytes(b"x")
        return {"local_path": str(local_path), "file_size_bytes": 1, "file_size_mb": 0.0}

    with patch("src.media_capture._pull_file_from_device", side_effect=fake_pull):
        res = await mc.take_screenshot(filename=spaced_name, pull_to_local=True, device_id="emulator-5554")

    assert res["success"] is True

    # screencap must use the quoted device path
    capture_cmds = [c for c in adb.commands if "screencap" in c]
    assert capture_cmds, "screencap command was not issued"
    assert quoted_device_path in capture_cmds[0], (
        f"expected {quoted_device_path!r} in command, got {capture_cmds[0]!r}"
    )
    # unquoted form must not appear verbatim (would contain the raw space)
    assert f"screencap -p {expected_device_path}" not in capture_cmds[0]

    # rm cleanup must use the quoted device path
    rm_cmds = [c for c in adb.commands if " shell rm " in c]
    assert rm_cmds, "rm cleanup command was not issued"
    assert quoted_device_path in rm_cmds[0]

    # screenrecord (start_recording) must also use quoted device path
    from src.media_capture import VideoRecorder

    with patch("asyncio.create_subprocess_exec") as mock_exec:
        fake_proc = AsyncMock()
        fake_proc.pid = 4242
        fake_proc.returncode = None
        mock_exec.return_value = fake_proc

        vr = VideoRecorder(adb_manager=adb, output_dir=str(tmp_path))
        rec_res = await vr.start_recording(
            filename="my recording.mp4", time_limit=1
        , device_id="emulator-5554")
        assert rec_res["success"] is True

        # The exec call's argv is the shlex.split of the formatted command; the
        # final positional should be the unquoted device path (shell-level quoting
        # is consumed by shlex.split). Assert the raw command string used to build
        # the argv was quoted by inspecting the last argv entry.
        called_args, _ = mock_exec.call_args
        # Last arg in the list is the device path after shlex.split. Verify it
        # equals the (unquoted) device path — i.e., shlex.split correctly parsed
        # the quoted token.
        assert called_args[-1] == "/sdcard/my recording.mp4", (
            f"expected device path argv to round-trip through shlex.quote/split, "
            f"got argv={called_args!r}"
        )
