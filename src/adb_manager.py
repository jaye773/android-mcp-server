"""ADB Manager for Android device communication."""

import asyncio
import logging
import shlex
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Tuple, ClassVar

logger = logging.getLogger(__name__)


class ADBCommands:
    """Standardized ADB command patterns."""

    DEVICES_LIST: ClassVar[str] = "adb devices -l"
    DEVICE_INFO: ClassVar[str] = "adb -s {device} shell getprop"

    UI_DUMP: ClassVar[str] = "adb -s {device} shell uiautomator dump"
    UI_DUMP_COMPRESSED: ClassVar[str] = (
        "adb -s {device} shell uiautomator dump --compressed"
    )

    TAP: ClassVar[str] = "adb -s {device} shell input tap {x} {y}"
    SWIPE: ClassVar[str] = (
        "adb -s {device} shell input swipe {x1} {y1} {x2} {y2} {duration}"
    )
    TEXT_INPUT: ClassVar[str] = "adb -s {device} shell input text {text}"
    KEY_EVENT: ClassVar[str] = "adb -s {device} shell input keyevent {keycode}"

    SCREENSHOT: ClassVar[str] = "adb -s {device} shell screencap -p"
    SCREEN_RECORD: ClassVar[str] = "adb -s {device} shell screenrecord {options} {path}"

    LOGCAT: ClassVar[str] = "adb -s {device} logcat {options}"
    LOGCAT_CLEAR: ClassVar[str] = "adb -s {device} logcat -c"


class ADBManager:
    """Handles ADB device connections and command execution."""

    def __init__(self) -> None:
        self.selected_device: Optional[str] = None
        self.devices_cache: Dict[str, Any] = {}
        self._last_device_check: Optional[datetime] = None
        self._device_cache_ttl: int = 30  # seconds

    async def list_devices(self) -> List[Dict[str, Any]]:
        """List all connected Android devices."""
        try:
            result = await self.execute_adb_command(
                ADBCommands.DEVICES_LIST, check_device=False, timeout=10
            )

            if not result["success"]:
                return []

            devices = []
            lines = result["stdout"].strip().split("\n")[1:]  # Skip header

            for line in lines:
                if not line.strip():
                    continue

                parts = line.split()
                if len(parts) < 2:
                    continue

                device_id = parts[0]
                status = parts[1]

                # Parse additional info
                info = {"id": device_id, "status": status}
                if len(parts) > 2:
                    for part in parts[2:]:
                        if ":" in part:
                            key, value = part.split(":", 1)
                            info[key] = value

                devices.append(info)

            return devices

        except Exception as e:
            logger.error(f"Failed to list devices: {e}")
            return []

    async def auto_select_device(self) -> Dict[str, Any]:
        """
        Auto-selection priority:
        1. Previously selected device (if still connected)
        2. First device with 'device' status
        3. First emulator if no physical devices
        4. Error if no devices available
        """
        devices = await self.list_devices()

        if not devices:
            return {
                "success": False,
                "error": "No Android devices connected",
                "devices": [],
            }

        # Priority 1: Previously selected device
        if self.selected_device:
            for device in devices:
                if (
                    device["id"] == self.selected_device
                    and device["status"] == "device"
                ):
                    return {
                        "success": True,
                        "selected": device,
                        "reason": "previous_selection",
                    }

        # Priority 2: First device with 'device' status
        physical_devices = [
            d for d in devices if d["status"] == "device" and "emulator" not in d["id"]
        ]
        if physical_devices:
            selected = physical_devices[0]
            self.selected_device = selected["id"]
            return {"success": True, "selected": selected, "reason": "first_physical"}

        # Priority 3: First emulator
        emulators = [
            d for d in devices if "emulator" in d["id"] and d["status"] == "device"
        ]
        if emulators:
            selected = emulators[0]
            self.selected_device = selected["id"]
            return {"success": True, "selected": selected, "reason": "first_emulator"}

        return {
            "success": False,
            "error": "No devices in 'device' status",
            "devices": devices,
        }

    async def execute_adb_command(
        self,
        command: str,
        timeout: int = 30,
        capture_output: bool = True,
        check_device: bool = True,
    ) -> Dict[str, Any]:
        """
        Robust ADB command execution with error handling.
        """
        if check_device and not self.selected_device:
            device_result = await self.auto_select_device()
            if not device_result["success"]:
                return device_result

        try:
            # Format command with device ID
            if "{device}" in command and self.selected_device:
                formatted_command = command.format(device=self.selected_device)
            else:
                formatted_command = command

            # Safely split command for subprocess
            cmd_parts = shlex.split(formatted_command)

            # Execute with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE if capture_output else None,
                stderr=asyncio.subprocess.PIPE,
            )
            # Determine effective timeout using any active tool deadline
            effective_timeout = float(timeout)
            try:
                from .timeout import has_deadline, remaining_time as _remaining_time
                if has_deadline():
                    effective_timeout = max(0.1, min(effective_timeout, _remaining_time()))
            except Exception:
                effective_timeout = float(timeout)

            try:
                # Enforce timeout using context manager (Python 3.11+)
                async with asyncio.timeout(effective_timeout):
                    stdout, stderr = await process.communicate()
            except (asyncio.TimeoutError, TimeoutError):
                # Graceful termination on timeout
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass
                try:
                    async with asyncio.timeout(1.0):
                        await process.communicate()
                except Exception:
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
                    try:
                        async with asyncio.timeout(1.0):
                            await process.communicate()
                    except Exception:
                        pass
                return {
                    "success": False,
                    "error": f"Command timed out after {effective_timeout} seconds",
                    "command": formatted_command,
                }

            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode("utf-8") if stdout else "",
                "stderr": stderr.decode("utf-8") if stderr else "",
                "returncode": process.returncode,
                "command": formatted_command,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Command execution failed: {str(e)}",
                "command": formatted_command,
            }

    async def check_device_health(
        self, device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check if device is responsive and ready."""
        device_id = device_id or self.selected_device
        if not device_id:
            return {"success": False, "error": "No device selected"}

        health_checks = [
            ("connectivity", f"adb -s {device_id} shell echo 'connected'"),
            (
                "screen_state",
                f"adb -s {device_id} shell dumpsys power | grep 'Display Power'",
            ),
            ("ui_service", f"adb -s {device_id} shell service check uiautomator"),
        ]

        results = {}
        for check_name, command in health_checks:
            result = await self.execute_adb_command(
                command, timeout=10, check_device=False
            )
            results[check_name] = {
                "passed": (
                    result["success"]
                    and "connected" in result.get("stdout", "").lower()
                ),
                "details": result.get("stdout", "").strip(),
            }

        overall_health = all(check["passed"] for check in results.values())
        return {
            "success": True,
            "healthy": overall_health,
            "checks": results,
            "device_id": device_id,
        }

    async def get_device_info(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed device information."""
        device_id = device_id or self.selected_device
        if not device_id:
            return {"success": False, "error": "No device selected"}

        try:
            result = await self.execute_adb_command(
                ADBCommands.DEVICE_INFO.format(device=device_id), check_device=False
            )

            if not result["success"]:
                return result

            # Parse device properties
            properties = {}
            for line in result["stdout"].split("\n"):
                if ": [" in line and "]" in line:
                    prop_line = line.strip()
                    if prop_line.startswith("[") and "]: [" in prop_line:
                        key_end = prop_line.find("]: [")
                        value_start = key_end + 4
                        value_end = prop_line.rfind("]")

                        key = prop_line[1:key_end]
                        value = prop_line[value_start:value_end]
                        properties[key] = value

            # Extract key information
            device_info = {
                "device_id": device_id,
                "model": properties.get("ro.product.model", "Unknown"),
                "manufacturer": properties.get("ro.product.manufacturer", "Unknown"),
                "android_version": properties.get(
                    "ro.build.version.release", "Unknown"
                ),
                "api_level": properties.get("ro.build.version.sdk", "Unknown"),
                "serial": properties.get("ro.serialno", device_id),
                "all_properties": properties,
            }

            return {"success": True, "device_info": device_info}

        except Exception as e:
            return {"success": False, "error": f"Failed to get device info: {str(e)}"}

    async def get_screen_size(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """Get device screen dimensions."""
        device_id = device_id or self.selected_device
        if not device_id:
            return {"success": False, "error": "No device selected"}

        try:
            result = await self.execute_adb_command(
                f"adb -s {device_id} shell wm size", check_device=False
            )

            if not result["success"]:
                return result

            # Parse output like "Physical size: 1080x2340"
            output = result["stdout"].strip()
            if ":" in output:
                size_part = output.split(":", 1)[1].strip()
                if "x" in size_part:
                    width, height = size_part.split("x")
                    return {
                        "success": True,
                        "width": int(width),
                        "height": int(height),
                        "raw_output": output,
                    }

            return {"success": False, "error": f"Could not parse screen size: {output}"}

        except Exception as e:
            return {"success": False, "error": f"Failed to get screen size: {str(e)}"}

    async def get_foreground_app(self, device_id: Optional[str] = None, timeout: int = 5) -> Dict[str, Any]:
        """Detect the currently foreground app (package/activity).

        Tries multiple dumpsys sources for robustness and parses common formats like:
        - mCurrentFocus=Window{... u0 com.android.chrome/com.google.android.apps.chrome.Main}
        - mResumedActivity: ActivityRecord{... com.android.chrome/com.google.android.apps.chrome.Main}
        """
        device_id = device_id or self.selected_device
        if not device_id:
            return {"success": False, "error": "No device selected"}

        commands = [
            f"adb -s {device_id} shell dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'",
            f"adb -s {device_id} shell dumpsys activity activities | grep mResumedActivity",
            f"adb -s {device_id} shell dumpsys activity | grep mResumedActivity",
        ]

        pattern = re.compile(r"([a-zA-Z0-9_\.]+)/(?:[a-zA-Z0-9_\.]+)")

        for cmd in commands:
            try:
                result = await self.execute_adb_command(cmd, timeout=timeout, check_device=False)
                if not result.get("success"):
                    continue
                out = (result.get("stdout") or "").strip()
                m = pattern.search(out)
                if m:
                    pkg = m.group(1)
                    # Try to capture full activity if present
                    # Split on space, last token typically contains pkg/activity
                    act = None
                    tokens = out.split()
                    for tok in reversed(tokens):
                        if "/" in tok and tok.count("/") == 1:
                            act = tok.split("/", 1)[1].strip()
                            break
                    return {
                        "success": True,
                        "package": pkg,
                        "activity": act,
                        "source": cmd,
                        "raw": out,
                    }
            except Exception:
                continue

        return {"success": False, "error": "Unable to detect foreground app"}
