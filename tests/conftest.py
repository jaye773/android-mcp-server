"""Test configuration and fixtures for Android MCP Server tests."""

import asyncio
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, Mock, MagicMock
from typing import Dict, Any, List, Optional, AsyncGenerator, Generator

from src.adb_manager import ADBManager, ADBCommands
from src.ui_inspector import UILayoutExtractor, ElementFinder
from src.screen_interactor import ScreenInteractor, GestureController, TextInputController
from src.media_capture import MediaCapture, VideoRecorder
from src.log_monitor import LogMonitor
from src.validation import ComprehensiveValidator, SecurityLevel
from src.error_handler import ErrorHandler
from src.feedback_system import FeedbackSystem


# Test Data Constants
MOCK_DEVICE_ID = "emulator-5554"
MOCK_DEVICE_INFO = {
    "id": MOCK_DEVICE_ID,
    "status": "device",
    "model": "Android Test Device",
    "product": "sdk_gphone_x86",
    "transport_id": "1"
}

MOCK_SCREEN_SIZE = {"width": 1080, "height": 1920}

MOCK_UI_ELEMENT = {
    "index": "0",
    "text": "Test Button",
    "resource-id": "com.test:id/button",
    "class": "android.widget.Button",
    "package": "com.test",
    "content-desc": "Test button description",
    "checkable": "false",
    "checked": "false",
    "clickable": "true",
    "enabled": "true",
    "focusable": "true",
    "focused": "false",
    "scrollable": "false",
    "long-clickable": "false",
    "password": "false",
    "selected": "false",
    "bounds": "[100,200][300,400]"
}

MOCK_UI_DUMP_XML = f"""<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="{MOCK_UI_ELEMENT['text']}"
        resource-id="{MOCK_UI_ELEMENT['resource-id']}"
        class="{MOCK_UI_ELEMENT['class']}"
        package="{MOCK_UI_ELEMENT['package']}"
        content-desc="{MOCK_UI_ELEMENT['content-desc']}"
        checkable="{MOCK_UI_ELEMENT['checkable']}"
        checked="{MOCK_UI_ELEMENT['checked']}"
        clickable="{MOCK_UI_ELEMENT['clickable']}"
        enabled="{MOCK_UI_ELEMENT['enabled']}"
        focusable="{MOCK_UI_ELEMENT['focusable']}"
        focused="{MOCK_UI_ELEMENT['focused']}"
        scrollable="{MOCK_UI_ELEMENT['scrollable']}"
        long-clickable="{MOCK_UI_ELEMENT['long-clickable']}"
        password="{MOCK_UI_ELEMENT['password']}"
        selected="{MOCK_UI_ELEMENT['selected']}"
        bounds="{MOCK_UI_ELEMENT['bounds']}" />
</hierarchy>"""


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def mock_adb_process() -> Mock:
    """Mock subprocess process for ADB commands."""
    process_mock = Mock()
    process_mock.communicate.return_value = (b"", b"")
    process_mock.returncode = 0
    process_mock.stdout = b""
    process_mock.stderr = b""
    return process_mock


@pytest.fixture
def mock_successful_adb_result() -> Dict[str, Any]:
    """Standard successful ADB command result."""
    return {
        "success": True,
        "stdout": "mock output",
        "stderr": "",
        "return_code": 0,
        "command": "mock adb command"
    }


@pytest.fixture
def mock_failed_adb_result() -> Dict[str, Any]:
    """Standard failed ADB command result."""
    return {
        "success": False,
        "stdout": "",
        "stderr": "mock error",
        "return_code": 1,
        "command": "mock adb command",
        "error": "Command failed with return code 1"
    }


@pytest.fixture
def mock_device_list() -> List[Dict[str, Any]]:
    """Mock list of connected devices."""
    return [
        {
            "id": "emulator-5554",
            "status": "device",
            "model": "Android Test Device 1",
            "product": "sdk_gphone_x86",
            "transport_id": "1"
        },
        {
            "id": "emulator-5556",
            "status": "device",
            "model": "Android Test Device 2",
            "product": "sdk_gphone_x86_64",
            "transport_id": "2"
        }
    ]


@pytest.fixture
def mock_adb_manager() -> AsyncMock:
    """Mock ADB manager with common methods."""
    adb_mock = AsyncMock(spec=ADBManager)
    adb_mock.selected_device = MOCK_DEVICE_ID
    adb_mock.devices_cache = {}

    # Mock device operations
    adb_mock.list_devices.return_value = [MOCK_DEVICE_INFO]
    adb_mock.auto_select_device.return_value = {
        "success": True,
        "selected": MOCK_DEVICE_INFO,
        "health": {"status": "healthy", "battery_level": 85}
    }
    adb_mock.get_device_info.return_value = {
        "success": True,
        "device_info": MOCK_DEVICE_INFO
    }
    adb_mock.get_screen_size.return_value = MOCK_SCREEN_SIZE
    adb_mock.check_device_health.return_value = {
        "status": "healthy",
        "battery_level": 85,
        "available_storage": "2GB",
        "system_load": "low"
    }

    # Mock command execution with proper handling for UI dump operations
    def mock_execute_command(cmd, timeout=30):
        if "uiautomator dump" in cmd:
            return {
                "success": True,
                "stdout": "",
                "stderr": "",
                "return_code": 0
            }
        elif "cat /sdcard/window_dump.xml" in cmd:
            # Import here to avoid circular import
            from tests.mocks.adb_mock import MockUIScenarios
            return {
                "success": True,
                "stdout": MockUIScenarios.login_screen(),
                "stderr": "",
                "return_code": 0
            }
        elif "test -f /sdcard/window_dump.xml" in cmd:
            return {
                "success": True,
                "stdout": "exists",
                "stderr": "",
                "return_code": 0
            }
        else:
            return {
                "success": True,
                "stdout": "mock output",
                "stderr": "",
                "return_code": 0
            }

    adb_mock.execute_adb_command.side_effect = mock_execute_command

    return adb_mock


@pytest.fixture
def mock_ui_inspector(mock_adb_manager) -> AsyncMock:
    """Mock UI inspector with layout extraction."""
    ui_mock = AsyncMock(spec=UILayoutExtractor)
    ui_mock.adb_manager = mock_adb_manager

    ui_mock.get_ui_layout.return_value = {
        "success": True,
        "xml_dump": MOCK_UI_DUMP_XML,
        "elements": [MOCK_UI_ELEMENT],
        "element_count": 1
    }

    # Additional mock methods can be added as needed

    return ui_mock


@pytest.fixture
def mock_element_finder(mock_ui_inspector) -> AsyncMock:
    """Mock element finder for UI search operations."""
    finder_mock = AsyncMock(spec=ElementFinder)
    finder_mock.ui_inspector = mock_ui_inspector

    finder_mock.find_elements.return_value = [MOCK_UI_ELEMENT]
    finder_mock.find_best_element.return_value = MOCK_UI_ELEMENT
    finder_mock.element_to_dict.return_value = MOCK_UI_ELEMENT

    return finder_mock


@pytest.fixture
def mock_screen_interactor(mock_adb_manager, mock_ui_inspector) -> AsyncMock:
    """Mock screen interaction controller."""
    interactor_mock = AsyncMock(spec=ScreenInteractor)
    interactor_mock.adb_manager = mock_adb_manager
    interactor_mock.ui_inspector = mock_ui_inspector

    interactor_mock.tap_coordinates.return_value = {
        "success": True,
        "action": "tap",
        "coordinates": {"x": 100, "y": 200},
        "timestamp": "2024-01-01T00:00:00Z"
    }

    interactor_mock.tap_element.return_value = {
        "success": True,
        "action": "tap_element",
        "element": MOCK_UI_ELEMENT,
        "coordinates": {"x": 200, "y": 300}
    }

    return interactor_mock


@pytest.fixture
def mock_gesture_controller(mock_adb_manager) -> AsyncMock:
    """Mock gesture controller for swipe operations."""
    gesture_mock = AsyncMock(spec=GestureController)
    gesture_mock.adb_manager = mock_adb_manager

    gesture_mock.swipe_coordinates.return_value = {
        "success": True,
        "action": "swipe",
        "start": {"x": 100, "y": 200},
        "end": {"x": 300, "y": 400},
        "duration_ms": 300
    }

    gesture_mock.swipe_direction.return_value = {
        "success": True,
        "action": "swipe_direction",
        "direction": "up",
        "distance": 500,
        "duration_ms": 300
    }

    return gesture_mock


@pytest.fixture
def mock_text_controller(mock_adb_manager) -> AsyncMock:
    """Mock text input controller."""
    text_mock = AsyncMock(spec=TextInputController)
    text_mock.adb_manager = mock_adb_manager

    text_mock.input_text.return_value = {
        "success": True,
        "action": "input_text",
        "text": "test input",
        "clear_existing": False
    }

    text_mock.press_key.return_value = {
        "success": True,
        "action": "key_press",
        "keycode": "KEYCODE_ENTER"
    }

    return text_mock


@pytest.fixture
def mock_media_capture(mock_adb_manager, temp_dir) -> AsyncMock:
    """Mock media capture for screenshots."""
    media_mock = AsyncMock(spec=MediaCapture)
    media_mock.adb_manager = mock_adb_manager

    screenshot_path = temp_dir / "screenshot.png"
    screenshot_path.touch()  # Create empty file

    media_mock.take_screenshot.return_value = {
        "success": True,
        "filename": "screenshot.png",
        "local_path": str(screenshot_path),
        "device_path": "/sdcard/screenshot.png",
        "size": {"width": 1080, "height": 1920}
    }

    return media_mock


@pytest.fixture
def mock_video_recorder(mock_adb_manager, temp_dir) -> AsyncMock:
    """Mock video recorder for screen recording."""
    recorder_mock = AsyncMock(spec=VideoRecorder)
    recorder_mock.adb_manager = mock_adb_manager
    recorder_mock.active_recordings = {}

    video_path = temp_dir / "recording.mp4"
    video_path.touch()  # Create empty file

    recorder_mock.start_recording.return_value = {
        "success": True,
        "recording_id": "rec_001",
        "filename": "recording.mp4",
        "device_path": "/sdcard/recording.mp4",
        "time_limit": 180
    }

    recorder_mock.stop_recording.return_value = {
        "success": True,
        "recording_id": "rec_001",
        "filename": "recording.mp4",
        "local_path": str(video_path),
        "duration": 30
    }

    recorder_mock.list_active_recordings.return_value = {
        "success": True,
        "recordings": [],
        "count": 0
    }

    return recorder_mock


@pytest.fixture
def mock_log_monitor(mock_adb_manager) -> AsyncMock:
    """Mock log monitor for logcat operations."""
    monitor_mock = AsyncMock(spec=LogMonitor)
    monitor_mock.adb_manager = mock_adb_manager
    monitor_mock.active_monitors = {}

    monitor_mock.get_logcat.return_value = {
        "success": True,
        "logs": [
            "2024-01-01 00:00:01.000  1000  1001 I TestTag: Test log message 1",
            "2024-01-01 00:00:02.000  1000  1001 W TestTag: Test log message 2"
        ],
        "line_count": 2,
        "filter_criteria": {"tag": None, "priority": "V"}
    }

    monitor_mock.start_log_monitoring.return_value = {
        "success": True,
        "monitor_id": "monitor_001",
        "filter_criteria": {"tag": None, "priority": "I"},
        "output_file": None
    }

    monitor_mock.stop_log_monitoring.return_value = {
        "success": True,
        "monitor_id": "monitor_001",
        "lines_captured": 150
    }

    monitor_mock.list_active_monitors.return_value = {
        "success": True,
        "monitors": [],
        "count": 0
    }

    return monitor_mock


@pytest.fixture
def mock_validator() -> Mock:
    """Mock comprehensive validator."""
    validator_mock = Mock(spec=ComprehensiveValidator)
    validator_mock.security_level = SecurityLevel.STRICT

    # Mock validation results that are always valid by default
    from src.validation import ValidationResult
    valid_result = ValidationResult(True, {"text": "test"}, [], [])

    validator_mock.validate_element_search.return_value = valid_result
    validator_mock.validate_coordinates.return_value = valid_result
    validator_mock.validate_text_input.return_value = valid_result
    validator_mock.validate_key_input.return_value = valid_result

    return validator_mock


@pytest.fixture
def mock_error_handler() -> Mock:
    """Mock error handler system."""
    handler_mock = Mock(spec=ErrorHandler)

    handler_mock.handle_error.return_value = {
        "error_code": "TEST_ERROR",
        "message": "Test error occurred",
        "recovery_suggestions": ["Retry the operation", "Check device connection"]
    }

    return handler_mock


@pytest.fixture
def mock_feedback_system() -> Mock:
    """Mock feedback collection system."""
    feedback_mock = Mock()

    # Mock methods that exist on the actual FeedbackSystem
    feedback_mock.add_feedback_callback.return_value = None
    feedback_mock.send_feedback.return_value = None
    feedback_mock.send_progress.return_value = None

    # Mock progress tracker
    feedback_mock.progress_tracker.start_operation.return_value = Mock()
    feedback_mock.progress_tracker.complete_operation.return_value = Mock()
    feedback_mock.progress_tracker.fail_operation.return_value = Mock()

    # Mock message builder
    feedback_mock.message_builder.create_success_message.return_value = Mock()
    feedback_mock.message_builder.create_error_message.return_value = Mock()

    return feedback_mock


# Common test parameter combinations
@pytest.fixture
def valid_tap_params():
    """Valid parameters for tap operations."""
    return {"x": 100, "y": 200}


@pytest.fixture
def valid_swipe_params():
    """Valid parameters for swipe operations."""
    return {
        "start_x": 100,
        "start_y": 200,
        "end_x": 300,
        "end_y": 400,
        "duration_ms": 300
    }


@pytest.fixture
def valid_text_params():
    """Valid parameters for text input."""
    return {
        "text": "test input",
        "clear_existing": False
    }


@pytest.fixture
def valid_element_search_params():
    """Valid parameters for element search."""
    return {
        "text": "Test Button",
        "resource_id": "com.test:id/button",
        "content_desc": None,
        "class_name": None,
        "clickable_only": False,
        "enabled_only": True,
        "exact_match": False
    }


@pytest.fixture
def invalid_coordinates():
    """Invalid coordinate parameters for testing."""
    return [
        {"x": -1, "y": 200},  # Negative x
        {"x": 100, "y": -1},  # Negative y
        {"x": 10000, "y": 200},  # X out of bounds
        {"x": 100, "y": 10000},  # Y out of bounds
    ]


@pytest.fixture
def mock_server_components(
    mock_adb_manager,
    mock_ui_inspector,
    mock_screen_interactor,
    mock_gesture_controller,
    mock_text_controller,
    mock_media_capture,
    mock_video_recorder,
    mock_log_monitor,
    mock_validator,
    mock_error_handler,
    mock_feedback_system
):
    """All server components mocked for integration tests."""
    return {
        "adb_manager": mock_adb_manager,
        "ui_inspector": mock_ui_inspector,
        "screen_interactor": mock_screen_interactor,
        "gesture_controller": mock_gesture_controller,
        "text_controller": mock_text_controller,
        "media_capture": mock_media_capture,
        "video_recorder": mock_video_recorder,
        "log_monitor": mock_log_monitor,
        "validator": mock_validator,
        "error_handler": mock_error_handler,
        "feedback_system": mock_feedback_system
    }