"""Mock ADB infrastructure for testing without physical devices."""

import asyncio
import json
import random
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Union
from unittest.mock import AsyncMock, Mock


class MockADBCommand:
    """Mock ADB command execution with realistic responses."""

    # Mock device responses
    DEVICE_LIST_RESPONSES = {
        "no_devices": "List of devices attached\n\n",
        "single_device": "List of devices attached\nemulator-5554\tdevice\n",
        "multiple_devices": (
            "List of devices attached\n"
            "emulator-5554\tdevice\n"
            "emulator-5556\tdevice\n"
            "physical-device\tdevice\n"
        ),
        "offline_device": "List of devices attached\nemulator-5554\toffline\n",
        "unauthorized": "List of devices attached\nemulator-5554\tunauthorized\n",
    }

    # Mock device properties
    DEVICE_PROPERTIES = {
        "ro.product.model": "Android Test Device",
        "ro.product.brand": "Google",
        "ro.product.name": "sdk_gphone_x86",
        "ro.build.version.release": "13",
        "ro.build.version.sdk": "33",
        "ro.product.cpu.abi": "x86",
        "ro.hardware": "ranchu",
        "sys.boot_completed": "1",
        "ro.debuggable": "1",
        "ro.secure": "0",
    }

    # Mock UI dump XML structure
    UI_DUMP_TEMPLATE = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout"
        package="com.android.systemui" content-desc="" checkable="false"
        checked="false" clickable="false" enabled="true" focusable="false"
        focused="false" scrollable="false" long-clickable="false" password="false"
        selected="false" bounds="[0,0][1080,1920]">
    <node index="1" text="Test App" resource-id="com.test:id/title"
          class="android.widget.TextView" package="com.test" content-desc=""
          checkable="false" checked="false" clickable="false" enabled="true"
          focusable="false" focused="false" scrollable="false"
          long-clickable="false" password="false" selected="false"
          bounds="[100,100][500,200]" />
    <node index="2" text="Click Me" resource-id="com.test:id/button"
          class="android.widget.Button" package="com.test"
          content-desc="Test button" checkable="false" checked="false"
          clickable="true" enabled="true" focusable="true" focused="false"
          scrollable="false" long-clickable="false" password="false"
          selected="false" bounds="[200,300][400,400]" />
    <node index="3" text="" resource-id="com.test:id/input"
          class="android.widget.EditText" package="com.test"
          content-desc="Text input field" checkable="false" checked="false"
          clickable="true" enabled="true" focusable="true" focused="false"
          scrollable="false" long-clickable="false" password="false"
          selected="false" bounds="[100,500][600,600]" />
  </node>
</hierarchy>"""

    # Mock logcat messages
    LOGCAT_MESSAGES = [
        "01-01 00:00:01.000  1000  1001 I TestTag: Application started",
        "01-01 00:00:02.000  1000  1001 D TestTag: Debug message",
        "01-01 00:00:03.000  1000  1001 W TestTag: Warning message",
        "01-01 00:00:04.000  1000  1001 E TestTag: Error message",
        "01-01 00:00:05.000  1000  1001 V TestTag: Verbose message",
        "01-01 00:00:06.000  1000  1001 I TestTag: User interaction detected",
        "01-01 00:00:07.000  1000  1001 D TestTag: Processing user input",
        "01-01 00:00:08.000  1000  1001 I TestTag: Operation completed",
    ]

    @classmethod
    async def execute_command(
        cls, command: str, timeout: int = 30, device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mock ADB command execution with realistic delays and responses."""

        # Simulate command execution delay
        await asyncio.sleep(0.01 + random.uniform(0, 0.05))

        # Parse command type
        if "devices -l" in command:
            return cls._mock_devices_list()
        elif "shell getprop" in command:
            return cls._mock_getprop()
        elif "shell uiautomator dump" in command:
            return cls._mock_ui_dump(command)
        elif "shell input tap" in command:
            return cls._mock_input_tap(command)
        elif "shell input swipe" in command:
            return cls._mock_input_swipe(command)
        elif "shell input text" in command:
            return cls._mock_input_text(command)
        elif "shell input keyevent" in command:
            return cls._mock_keyevent(command)
        elif "shell screencap" in command:
            return cls._mock_screencap()
        elif "shell screenrecord" in command:
            return cls._mock_screenrecord(command)
        elif "logcat" in command:
            return cls._mock_logcat(command)
        elif "pull" in command:
            return cls._mock_pull(command)
        elif "push" in command:
            return cls._mock_push(command)
        else:
            return cls._mock_generic_success()

    @classmethod
    def _mock_devices_list(cls) -> Dict[str, Any]:
        """Mock device list command."""
        return {
            "success": True,
            "stdout": cls.DEVICE_LIST_RESPONSES["single_device"],
            "stderr": "",
            "return_code": 0,
            "command": "adb devices -l",
        }

    @classmethod
    def _mock_getprop(cls) -> Dict[str, Any]:
        """Mock getprop command for device properties."""
        props_output = "\n".join(
            [f"[{key}]: [{value}]" for key, value in cls.DEVICE_PROPERTIES.items()]
        )

        return {
            "success": True,
            "stdout": props_output,
            "stderr": "",
            "return_code": 0,
            "command": "adb shell getprop",
        }

    @classmethod
    def _mock_ui_dump(cls, command: str) -> Dict[str, Any]:
        """Mock UI dump command."""
        return {
            "success": True,
            "stdout": cls.UI_DUMP_TEMPLATE,
            "stderr": "",
            "return_code": 0,
            "command": command,
        }

    @classmethod
    def _mock_input_tap(cls, command: str) -> Dict[str, Any]:
        """Mock tap command."""
        return {
            "success": True,
            "stdout": "",
            "stderr": "",
            "return_code": 0,
            "command": command,
        }

    @classmethod
    def _mock_input_swipe(cls, command: str) -> Dict[str, Any]:
        """Mock swipe command."""
        return {
            "success": True,
            "stdout": "",
            "stderr": "",
            "return_code": 0,
            "command": command,
        }

    @classmethod
    def _mock_input_text(cls, command: str) -> Dict[str, Any]:
        """Mock text input command."""
        return {
            "success": True,
            "stdout": "",
            "stderr": "",
            "return_code": 0,
            "command": command,
        }

    @classmethod
    def _mock_keyevent(cls, command: str) -> Dict[str, Any]:
        """Mock key event command."""
        return {
            "success": True,
            "stdout": "",
            "stderr": "",
            "return_code": 0,
            "command": command,
        }

    @classmethod
    def _mock_screencap(cls) -> Dict[str, Any]:
        """Mock screenshot command."""
        # Simulate PNG binary data
        mock_png_header = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        return {
            "success": True,
            "stdout": mock_png_header + b"mock_image_data" * 100,
            "stderr": "",
            "return_code": 0,
            "command": "adb shell screencap -p",
        }

    @classmethod
    def _mock_screenrecord(cls, command: str) -> Dict[str, Any]:
        """Mock screen recording command."""
        return {
            "success": True,
            "stdout": "Recording started",
            "stderr": "",
            "return_code": 0,
            "command": command,
        }

    @classmethod
    def _mock_logcat(cls, command: str) -> Dict[str, Any]:
        """Mock logcat command."""
        # Return a subset of mock log messages
        log_output = "\n".join(cls.LOGCAT_MESSAGES[:5])

        return {
            "success": True,
            "stdout": log_output,
            "stderr": "",
            "return_code": 0,
            "command": command,
        }

    @classmethod
    def _mock_pull(cls, command: str) -> Dict[str, Any]:
        """Mock file pull command."""
        return {
            "success": True,
            "stdout": "1 file pulled, 0 skipped.",
            "stderr": "",
            "return_code": 0,
            "command": command,
        }

    @classmethod
    def _mock_push(cls, command: str) -> Dict[str, Any]:
        """Mock file push command."""
        return {
            "success": True,
            "stdout": "1 file pushed, 0 skipped.",
            "stderr": "",
            "return_code": 0,
            "command": command,
        }

    @classmethod
    def _mock_generic_success(cls) -> Dict[str, Any]:
        """Generic successful command response."""
        return {
            "success": True,
            "stdout": "Command executed successfully",
            "stderr": "",
            "return_code": 0,
            "command": "unknown command",
        }


class MockDeviceScenarios:
    """Predefined device scenarios for testing various conditions."""

    @staticmethod
    def healthy_device() -> Dict[str, Any]:
        """Mock a healthy, responsive device."""
        return {
            "device_id": "emulator-5554",
            "status": "device",
            "properties": MockADBCommand.DEVICE_PROPERTIES,
            "screen_size": {"width": 1080, "height": 1920},
            "battery_level": 85,
            "available_storage": "2GB",
            "response_delay": 0.05,
        }

    @staticmethod
    def slow_device() -> Dict[str, Any]:
        """Mock a slow, but working device."""
        device = MockDeviceScenarios.healthy_device()
        device.update(
            {"response_delay": 2.0, "battery_level": 25, "available_storage": "500MB"}
        )
        return device

    @staticmethod
    def offline_device() -> Dict[str, Any]:
        """Mock an offline device."""
        return {
            "device_id": "emulator-5554",
            "status": "offline",
            "properties": {},
            "error": "Device is offline",
        }

    @staticmethod
    def unauthorized_device() -> Dict[str, Any]:
        """Mock an unauthorized device."""
        return {
            "device_id": "emulator-5554",
            "status": "unauthorized",
            "properties": {},
            "error": "Device unauthorized. Please check the confirmation dialog on your device.",
        }


class MockUIScenarios:
    """Mock UI scenarios for testing element interactions."""

    @staticmethod
    def empty_screen() -> str:
        """Mock empty screen with no interactive elements."""
        return """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout"
        package="com.android.systemui" content-desc="" checkable="false"
        bounds="[0,0][1080,1920]" />
</hierarchy>"""

    @staticmethod
    def login_screen() -> str:
        """Mock login screen with username/password fields."""
        return """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.LinearLayout"
        package="com.test.app" bounds="[0,0][1080,1920]">
    <node index="1" text="Login" resource-id="com.test:id/title"
          class="android.widget.TextView" bounds="[100,200][500,300]" />
    <node index="2" text="" resource-id="com.test:id/username"
          class="android.widget.EditText" content-desc="Username field"
          clickable="true" enabled="true" focusable="true"
          bounds="[100,400][600,500]" />
    <node index="3" text="" resource-id="com.test:id/password"
          class="android.widget.EditText" content-desc="Password field"
          clickable="true" enabled="true" focusable="true" password="true"
          bounds="[100,600][600,700]" />
    <node index="4" text="Login" resource-id="com.test:id/login_btn"
          class="android.widget.Button" clickable="true" enabled="true"
          bounds="[200,800][400,900]" />
  </node>
</hierarchy>"""

    @staticmethod
    def scrollable_list() -> str:
        """Mock scrollable list with multiple items."""
        return """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.ListView"
        package="com.test.app" scrollable="true" bounds="[0,0][1080,1920]">
    <node index="1" text="Item 1" resource-id="com.test:id/item_1"
          clickable="true" bounds="[50,100][1030,200]" />
    <node index="2" text="Item 2" resource-id="com.test:id/item_2"
          clickable="true" bounds="[50,200][1030,300]" />
    <node index="3" text="Item 3" resource-id="com.test:id/item_3"
          clickable="true" bounds="[50,300][1030,400]" />
  </node>
</hierarchy>"""


class MockErrorScenarios:
    """Mock error scenarios for testing error handling."""

    @staticmethod
    def adb_timeout_error() -> Dict[str, Any]:
        """Mock ADB command timeout."""
        return {
            "success": False,
            "stdout": "",
            "stderr": "timeout: failed to connect to device",
            "return_code": 1,
            "error": "Command timed out after 10 seconds",
        }

    @staticmethod
    def device_not_found_error() -> Dict[str, Any]:
        """Mock device not found error."""
        return {
            "success": False,
            "stdout": "",
            "stderr": "error: device 'unknown-device' not found",
            "return_code": 1,
            "error": "Device not found",
        }

    @staticmethod
    def permission_denied_error() -> Dict[str, Any]:
        """Mock permission denied error."""
        return {
            "success": False,
            "stdout": "",
            "stderr": "adb: permission denied",
            "return_code": 1,
            "error": "Permission denied",
        }

    @staticmethod
    def ui_service_unavailable_error() -> Dict[str, Any]:
        """Mock UI automator service unavailable."""
        return {
            "success": False,
            "stdout": "",
            "stderr": "ERROR: could not get idle state",
            "return_code": 1,
            "error": "UI Automator service unavailable",
        }


async def create_mock_adb_manager() -> AsyncMock:
    """Create a fully configured mock ADB manager."""
    adb_mock = AsyncMock()

    # Set up command execution mock
    adb_mock.execute_adb_command.side_effect = MockADBCommand.execute_command

    # Set up device management mocks
    adb_mock.selected_device = "emulator-5554"
    adb_mock.devices_cache = {}

    # Configure device health scenario
    device_scenario = MockDeviceScenarios.healthy_device()

    adb_mock.list_devices.return_value = [
        {
            "id": device_scenario["device_id"],
            "status": device_scenario["status"],
            "model": "Android Test Device",
            "product": "sdk_gphone_x86",
            "transport_id": "1",
        }
    ]

    adb_mock.get_device_info.return_value = {
        "success": True,
        "device_info": device_scenario["properties"],
    }

    adb_mock.get_screen_size.return_value = device_scenario["screen_size"]

    adb_mock.check_device_health.return_value = {
        "status": "healthy",
        "battery_level": device_scenario["battery_level"],
        "available_storage": device_scenario["available_storage"],
        "system_load": "low",
    }

    return adb_mock
