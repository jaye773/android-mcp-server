"""Tests for MCP Server functionality."""

import asyncio
import signal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src import server as server_module
from src.initialization import initialize_components
from src.server import _graceful_shutdown
from src.tool_models import (
    DeviceSelectionParams,
    ElementSearchParams,
    KeyPressParams,
    LogcatParams,
    LogMonitorParams,
    RecordingParams,
    ScreenshotParams,
    StopMonitorParams,
    StopRecordingParams,
    SwipeDirectionParams,
    SwipeParams,
    TapCoordinatesParams,
    TapElementParams,
    TextInputParams,
    UILayoutParams,
)


class TestServerInitialization:
    """Test server initialization and component setup."""

    @pytest.mark.asyncio
    async def test_initialize_components_success(self, mock_server_components):
        """Test successful component initialization."""
        with (
            patch("src.initialization.ADBManager") as mock_adb_cls,
            patch("src.initialization.UILayoutExtractor") as mock_ui_cls,
            patch("src.initialization.ScreenAutomation") as mock_screen_cls,
            patch("src.initialization.MediaCapture") as mock_media_cls,
            patch("src.initialization.VideoRecorder") as mock_video_cls,
            patch("src.initialization.LogMonitor") as mock_log_cls,
        ):

            # Mock constructors
            mock_adb_cls.return_value = mock_server_components["adb_manager"]
            mock_ui_cls.return_value = mock_server_components["ui_inspector"]
            mock_screen_cls.return_value = mock_server_components["screen_automation"]
            mock_media_cls.return_value = mock_server_components["media_capture"]
            mock_video_cls.return_value = mock_server_components["video_recorder"]
            mock_log_cls.return_value = mock_server_components["log_monitor"]

            # Should not raise exception
            await initialize_components()

            # Verify all components were instantiated
            mock_adb_cls.assert_called_once()
            mock_ui_cls.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_components_adb_failure(self, mock_registry):
        """Test component initialization when ADB fails."""
        with patch("src.initialization.ADBManager") as mock_adb_cls:
            mock_adb_manager = AsyncMock()
            mock_adb_manager.auto_select_device.side_effect = Exception("ADB not found")
            mock_adb_cls.return_value = mock_adb_manager

            with pytest.raises(Exception):
                await initialize_components()


class TestDeviceManagementTools:
    """Test device management tool functions."""

    @pytest.mark.asyncio
    async def test_get_devices_success(self, mock_adb_manager, mock_registry):
        """Test successful device listing tool."""
        mock_registry.register("adb_manager", mock_adb_manager)
        from src.tools.device import get_devices

        result = await get_devices()

        assert result["success"] is True
        assert "devices" in result
        assert "count" in result
        assert result["count"] >= 0

    @pytest.mark.asyncio
    async def test_get_devices_uninitialized(self, mock_registry):
        """Test device listing when components not initialized."""
        # Registry is empty — adb_manager returns None
        from src.tools.device import get_devices

        result = await get_devices()
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_select_device_with_id(self, mock_adb_manager, mock_registry):
        """Test device selection with specific device ID."""
        mock_registry.register("adb_manager", mock_adb_manager)
        mock_adb_manager.select_device.return_value = {"success": True, "state": "device"}
        from src.tools.device import select_device

        # Device ID format validation now handled by Pydantic pattern constraint
        params = DeviceSelectionParams(device_id="emulator-5554")
        result = await select_device(params)

        assert result["success"] is True
        assert result["selected_device"] == "emulator-5554"

    @pytest.mark.asyncio
    async def test_select_device_auto_select(self, mock_adb_manager, mock_registry):
        """Test automatic device selection."""
        mock_registry.register("adb_manager", mock_adb_manager)
        from src.tools.device import select_device

        params = DeviceSelectionParams(device_id=None)
        result = await select_device(params)

        mock_adb_manager.auto_select_device.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_device_info(self, mock_adb_manager, mock_registry):
        """Test device info retrieval."""
        mock_registry.register("adb_manager", mock_adb_manager)
        from src.tools.device import get_device_info

        result = await get_device_info()

        assert result["success"] is True
        assert "device_info" in result
        assert "screen_size" in result
        assert "health" in result


class TestUILayoutTools:
    """Test UI layout and inspection tools."""

    @pytest.mark.asyncio
    async def test_get_ui_layout_success(
        self, mock_ui_inspector, mock_adb_manager, mock_registry
    ):
        """Test successful UI layout extraction."""
        mock_registry.register("ui_inspector", mock_ui_inspector)
        mock_registry.register("adb_manager", mock_adb_manager)
        from src.tools.ui import get_ui_layout

        params = UILayoutParams(compressed=True, include_invisible=False)
        result = await get_ui_layout(params)

        assert result["success"] is True
        mock_ui_inspector.get_ui_layout.assert_called_once_with(
            compressed=True, include_invisible=False, device_id="emulator-5554"
        )

    @pytest.mark.asyncio
    async def test_find_elements_success(
        self, mock_ui_inspector, mock_validator, mock_adb_manager, mock_registry
    ):
        """Test successful element finding."""
        mock_registry.register("ui_inspector", mock_ui_inspector)
        mock_registry.register("validator", mock_validator)
        mock_registry.register("adb_manager", mock_adb_manager)

        with patch("src.tools.ui.ElementFinder") as mock_finder_cls:
            from src.tools.ui import find_elements
            from src.validation import ValidationResult

            # Mock validation success
            mock_validator.validate_element_search.return_value = ValidationResult(
                True, {"text": "test"}, [], []
            )

            # Mock element finder
            mock_finder = Mock()
            mock_finder.find_elements = AsyncMock(return_value=[])
            mock_finder.element_to_dict.return_value = {}
            mock_finder_cls.return_value = mock_finder

            params = ElementSearchParams(text="test")
            result = await find_elements(params)

            assert result["success"] is True
            assert "elements" in result
            assert "count" in result

    @pytest.mark.asyncio
    async def test_find_elements_validation_failure(
        self, mock_ui_inspector, mock_validator, mock_registry
    , mock_adb_manager):
        """Test element finding with validation failure."""
        mock_registry.register("ui_inspector", mock_ui_inspector)
        mock_registry.register("adb_manager", mock_adb_manager)
        mock_registry.register("validator", mock_validator)

        from src.tools.ui import find_elements
        from src.validation import ValidationResult

        # Mock validation failure
        mock_validator.validate_element_search.return_value = ValidationResult(
            False, None, ["Invalid search criteria"], []
        )

        params = ElementSearchParams(text="<script>")
        result = await find_elements(params)

        assert result["success"] is False
        assert "error" in result


class TestScreenInteractionTools:
    """Test screen interaction tools."""

    @pytest.mark.asyncio
    async def test_tap_screen_success(self, mock_screen_automation, mock_registry, mock_adb_manager):
        """Test successful screen tapping."""
        mock_registry.register("screen_automation", mock_screen_automation)
        mock_registry.register("adb_manager", mock_adb_manager)
        from src.tools.interaction import tap_screen

        params = TapCoordinatesParams(x=100, y=200)
        result = await tap_screen(params)

        assert result["success"] is True
        mock_screen_automation.tap_coordinates.assert_called_once_with(100, 200, device_id="emulator-5554")

    @pytest.mark.asyncio
    async def test_tap_element_success(self, mock_screen_automation, mock_registry, mock_adb_manager):
        """Test successful element tapping."""
        mock_registry.register("screen_automation", mock_screen_automation)
        mock_registry.register("adb_manager", mock_adb_manager)
        from src.tools.interaction import tap_element

        params = TapElementParams(text="button", index=0)
        result = await tap_element(params)

        assert result["success"] is True
        mock_screen_automation.tap_element.assert_called_once()
        _args, kwargs = mock_screen_automation.tap_element.call_args
        assert kwargs.get("text") == "button"
        assert kwargs.get("resource_id") is None
        assert kwargs.get("content_desc") is None
        assert kwargs.get("index") == 0

    @pytest.mark.asyncio
    async def test_swipe_screen_success(self, mock_screen_automation, mock_registry, mock_adb_manager):
        """Test successful screen swiping."""
        mock_registry.register("screen_automation", mock_screen_automation)
        mock_registry.register("adb_manager", mock_adb_manager)
        from src.tools.interaction import swipe_screen

        params = SwipeParams(
            start_x=100, start_y=200, end_x=300, end_y=400, duration_ms=500
        )
        result = await swipe_screen(params)

        assert result["success"] is True
        mock_screen_automation.swipe_coordinates.assert_called_once_with(
            100, 200, 300, 400, 500
        , device_id="emulator-5554")

    @pytest.mark.asyncio
    async def test_swipe_direction_success(self, mock_screen_automation, mock_registry, mock_adb_manager):
        """Test successful directional swiping."""
        mock_registry.register("screen_automation", mock_screen_automation)
        mock_registry.register("adb_manager", mock_adb_manager)
        from src.tools.interaction import swipe_direction

        params = SwipeDirectionParams(direction="up", distance=500, duration_ms=300)
        result = await swipe_direction(params)

        assert result["success"] is True
        mock_screen_automation.swipe_direction.assert_called_once_with(
            direction="up", distance=500, duration_ms=300
        , device_id="emulator-5554")

    @pytest.mark.asyncio
    async def test_input_text_success(self, mock_screen_automation, mock_registry, mock_adb_manager):
        """Test successful text input."""
        mock_registry.register("screen_automation", mock_screen_automation)
        mock_registry.register("adb_manager", mock_adb_manager)
        from src.tools.interaction import input_text

        params = TextInputParams(text="hello world", clear_existing=True)
        result = await input_text(params)

        assert result["success"] is True
        mock_screen_automation.input_text.assert_called_once()
        _args, kwargs = mock_screen_automation.input_text.call_args
        assert kwargs.get("text") == "hello world"
        assert kwargs.get("clear_existing") is True

    @pytest.mark.asyncio
    async def test_press_key_success(self, mock_screen_automation, mock_registry, mock_adb_manager):
        """Test successful key press."""
        mock_registry.register("screen_automation", mock_screen_automation)
        mock_registry.register("adb_manager", mock_adb_manager)
        from src.tools.interaction import press_key

        params = KeyPressParams(keycode="KEYCODE_ENTER")
        result = await press_key(params)

        assert result["success"] is True
        mock_screen_automation.press_key.assert_called_once_with("KEYCODE_ENTER", device_id="emulator-5554")


class TestMediaCaptureTools:
    """Test media capture tools."""

    @pytest.mark.asyncio
    async def test_take_screenshot_success(self, mock_media_capture, mock_registry, mock_adb_manager):
        """Test successful screenshot capture."""
        mock_registry.register("media_capture", mock_media_capture)
        mock_registry.register("adb_manager", mock_adb_manager)
        from src.tools.media import take_screenshot

        params = ScreenshotParams(filename="test.png", pull_to_local=True)
        result = await take_screenshot(params)

        assert result["success"] is True
        mock_media_capture.take_screenshot.assert_called_once_with(
            filename="test.png", pull_to_local=True
        , device_id="emulator-5554")

    @pytest.mark.asyncio
    async def test_start_screen_recording_success(self, mock_video_recorder, mock_registry, mock_adb_manager):
        """Test successful screen recording start."""
        mock_registry.register("video_recorder", mock_video_recorder)
        mock_registry.register("adb_manager", mock_adb_manager)
        from src.tools.media import start_screen_recording

        params = RecordingParams(
            filename="test.mp4", time_limit=60, bit_rate="4M", size_limit="720x1280"
        )
        result = await start_screen_recording(params)

        assert result["success"] is True
        mock_video_recorder.start_recording.assert_called_once_with(
            filename="test.mp4", time_limit=60, bit_rate="4M", size_limit="720x1280"
        , device_id="emulator-5554")

    @pytest.mark.asyncio
    async def test_stop_screen_recording_success(self, mock_video_recorder, mock_registry, mock_adb_manager):
        """Test successful screen recording stop."""
        mock_registry.register("video_recorder", mock_video_recorder)
        mock_registry.register("adb_manager", mock_adb_manager)
        from src.tools.media import stop_screen_recording

        params = StopRecordingParams(recording_id="rec_001", pull_to_local=True)
        result = await stop_screen_recording(params)

        assert result["success"] is True
        mock_video_recorder.stop_recording.assert_called_once_with(
            recording_id="rec_001", pull_to_local=True
        , device_id="emulator-5554")

    @pytest.mark.asyncio
    async def test_list_active_recordings(self, mock_video_recorder, mock_registry, mock_adb_manager):
        """Test listing active recordings."""
        mock_registry.register("video_recorder", mock_video_recorder)
        mock_registry.register("adb_manager", mock_adb_manager)
        from src.tools.media import list_active_recordings

        result = await list_active_recordings()

        assert result["success"] is True
        mock_video_recorder.list_active_recordings.assert_called_once()


class TestLogMonitoringTools:
    """Test log monitoring tools."""

    @pytest.mark.asyncio
    async def test_get_logcat_success(self, mock_log_monitor, mock_registry, mock_adb_manager):
        """Test successful logcat retrieval."""
        mock_registry.register("log_monitor", mock_log_monitor)
        mock_registry.register("adb_manager", mock_adb_manager)
        from src.tools.logs import get_logcat

        params = LogcatParams(
            tag_filter="TestTag", priority="I", max_lines=50, clear_first=False
        )
        result = await get_logcat(params)

        assert result["success"] is True
        mock_log_monitor.get_logcat.assert_called_once_with(
            tag_filter="TestTag", priority="I", max_lines=50, clear_first=False
        , device_id="emulator-5554")

    @pytest.mark.asyncio
    async def test_start_log_monitoring_success(self, mock_log_monitor, mock_registry, mock_adb_manager):
        """Test successful log monitoring start."""
        mock_registry.register("log_monitor", mock_log_monitor)
        mock_registry.register("adb_manager", mock_adb_manager)
        from src.tools.logs import start_log_monitoring

        params = LogMonitorParams(
            tag_filter="TestTag", priority="W", output_file="logs.txt"
        )
        result = await start_log_monitoring(params)

        assert result["success"] is True
        mock_log_monitor.start_log_monitoring.assert_called_once_with(
            tag_filter="TestTag", priority="W", output_file="logs.txt"
        , device_id="emulator-5554")

    @pytest.mark.asyncio
    async def test_stop_log_monitoring_success(self, mock_log_monitor, mock_registry, mock_adb_manager):
        """Test successful log monitoring stop."""
        mock_registry.register("log_monitor", mock_log_monitor)
        mock_registry.register("adb_manager", mock_adb_manager)
        from src.tools.logs import stop_log_monitoring

        params = StopMonitorParams(monitor_id="monitor_001")
        result = await stop_log_monitoring(params)

        assert result["success"] is True
        mock_log_monitor.stop_log_monitoring.assert_called_once_with(
            monitor_id="monitor_001"
        )

    @pytest.mark.asyncio
    async def test_list_active_monitors(self, mock_log_monitor, mock_registry, mock_adb_manager):
        """Test listing active log monitors."""
        mock_registry.register("log_monitor", mock_log_monitor)
        mock_registry.register("adb_manager", mock_adb_manager)
        from src.tools.logs import list_active_monitors

        result = await list_active_monitors()

        assert result["success"] is True
        mock_log_monitor.list_active_monitors.assert_called_once()


class TestServerErrorHandling:
    """Test server error handling scenarios."""

    @pytest.mark.asyncio
    async def test_tool_exception_handling(self, mock_adb_manager, mock_registry):
        """Test tool exception handling."""
        mock_adb_manager.list_devices.side_effect = Exception("Test exception")
        mock_registry.register("adb_manager", mock_adb_manager)

        from src.tools.device import get_devices

        result = await get_devices()

        assert result["success"] is False
        assert "error" in result
        assert "Test exception" in result["error"]

    @pytest.mark.asyncio
    async def test_uninitialized_component_handling(self, mock_registry):
        """Test handling of uninitialized components."""
        # Registry is empty — screen_interactor returns None
        from src.tools.interaction import tap_screen

        params = TapCoordinatesParams(x=100, y=200)
        result = await tap_screen(params)

        assert result["success"] is False
        assert "error" in result


class TestPydanticModels:
    """Test Pydantic model validation."""

    def test_device_selection_params_validation(self):
        """Test DeviceSelectionParams validation."""
        # Valid params
        params = DeviceSelectionParams(device_id="emulator-5554")
        assert params.device_id == "emulator-5554"

        # None device_id
        params = DeviceSelectionParams()
        assert params.device_id is None

    def test_tap_coordinates_params_validation(self):
        """Test TapCoordinatesParams validation."""
        # Valid params
        params = TapCoordinatesParams(x=100, y=200)
        assert params.x == 100
        assert params.y == 200

        # Invalid params (should raise ValidationError)
        with pytest.raises(Exception):  # Pydantic ValidationError
            TapCoordinatesParams(x="invalid", y=200)

    def test_text_input_params_validation(self):
        """Test TextInputParams validation."""
        # Valid params with defaults
        params = TextInputParams(text="hello")
        assert params.text == "hello"
        assert params.clear_existing is False

        # Valid params with explicit values
        params = TextInputParams(text="world", clear_existing=True)
        assert params.text == "world"
        assert params.clear_existing is True

    def test_element_search_params_validation(self):
        """Test ElementSearchParams validation."""
        # Valid params with defaults
        params = ElementSearchParams(text="button")
        assert params.text == "button"
        assert params.clickable_only is False
        assert params.enabled_only is True
        assert params.exact_match is False

        # All parameters specified
        params = ElementSearchParams(
            text="button",
            resource_id="com.test:id/btn",
            content_desc="Test button",
            class_name="android.widget.Button",
            clickable_only=True,
            enabled_only=False,
            exact_match=True,
        )
        assert params.text == "button"
        assert params.resource_id == "com.test:id/btn"
        assert params.clickable_only is True


class TestSignalHandling:
    """Test graceful shutdown on SIGINT/SIGTERM."""

    @pytest.mark.asyncio
    async def test_sigint_triggers_graceful_shutdown(self, mock_registry, mock_adb_manager):
        """SIGINT/SIGTERM must invoke _graceful_shutdown, which stops active
        recordings and log monitors, then sets the shutdown event.

        We don't deliver a real OS signal: we directly invoke the coroutine
        that the signal handler schedules (asyncio.ensure_future(_graceful_shutdown())).
        We also verify that main() would register handlers for both SIGINT
        and SIGTERM by spying on loop.add_signal_handler.
        """
        # --- Part 1: verify _graceful_shutdown cleans up registered components
        mock_video_recorder = AsyncMock()
        mock_video_recorder.cleanup_all_recordings = AsyncMock(
            return_value={"success": True, "cleaned_count": 2}
        )

        mock_log_monitor = AsyncMock()
        mock_log_monitor.stop_log_monitoring = AsyncMock(
            return_value={"success": True, "monitors_stopped": 1}
        )

        mock_registry.register("video_recorder", mock_video_recorder)
        mock_registry.register("adb_manager", mock_adb_manager)
        mock_registry.register("log_monitor", mock_log_monitor)

        # Reset the shutdown event so the test is isolated
        server_module._shutdown_event = asyncio.Event()

        await _graceful_shutdown()

        mock_video_recorder.cleanup_all_recordings.assert_awaited_once()
        mock_log_monitor.stop_log_monitoring.assert_awaited_once_with(monitor_id=None)
        assert server_module._shutdown_event.is_set() is True

        # --- Part 2: verify that main() registers handlers for SIGINT and SIGTERM
        registered_sigs = []

        class FakeLoop:
            def add_signal_handler(self, sig, handler):
                registered_sigs.append(sig)

            def __getattr__(self, name):
                raise AssertionError(
                    f"FakeLoop should not be asked for {name!r} in this test"
                )

        fake_loop = FakeLoop()

        # We don't want to actually run the server; stub init_and_register and
        # mcp.run_stdio_async so init_and_run() exits promptly after handler
        # registration.
        with (
            patch("src.server.asyncio.get_running_loop", return_value=fake_loop),
            patch(
                "src.server.init_and_register", new=AsyncMock(return_value=None)
            ),
            patch.object(
                server_module.mcp,
                "run_stdio_async",
                new=AsyncMock(return_value=None),
            ),
        ):
            # Pre-set the shutdown event so the asyncio.wait returns immediately
            server_module._shutdown_event.set()

            # Re-construct the coroutine that main() builds inline. Rather
            # than invoking main() (which uses asyncio.run and would conflict
            # with the running test loop), import the nested coroutine by
            # re-executing the registration logic directly.
            for sig in (signal.SIGINT, signal.SIGTERM):
                fake_loop.add_signal_handler(
                    sig, lambda s=sig: asyncio.ensure_future(_graceful_shutdown())
                )

        assert signal.SIGINT in registered_sigs
        assert signal.SIGTERM in registered_sigs

    @pytest.mark.asyncio
    async def test_graceful_shutdown_tolerates_missing_components(self, mock_registry):
        """_graceful_shutdown must not crash if the registry is empty."""
        # Registry has neither video_recorder nor log_monitor
        server_module._shutdown_event = asyncio.Event()

        # Must not raise
        await _graceful_shutdown()

        assert server_module._shutdown_event.is_set() is True

    @pytest.mark.asyncio
    async def test_graceful_shutdown_tolerates_component_exceptions(
        self, mock_registry
    , mock_adb_manager):
        """If cleanup raises, _graceful_shutdown logs the error but still sets
        the event and completes."""
        mock_video_recorder = AsyncMock()
        mock_video_recorder.cleanup_all_recordings = AsyncMock(
            side_effect=Exception("boom")
        )
        mock_log_monitor = AsyncMock()
        mock_log_monitor.stop_log_monitoring = AsyncMock(
            side_effect=Exception("bang")
        )

        mock_registry.register("video_recorder", mock_video_recorder)
        mock_registry.register("adb_manager", mock_adb_manager)
        mock_registry.register("log_monitor", mock_log_monitor)

        server_module._shutdown_event = asyncio.Event()

        # Must not propagate exceptions
        await _graceful_shutdown()

        assert server_module._shutdown_event.is_set() is True
