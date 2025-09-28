"""Extended tests for ADB Manager to achieve 75%+ code coverage."""

import pytest
import asyncio
import sys
from unittest.mock import AsyncMock, patch, Mock
from datetime import datetime, timedelta
import re

from src.adb_manager import ADBManager, ADBCommands
from tests.mocks import MockADBCommand, MockDeviceScenarios, MockErrorScenarios


class TestADBManagerDeviceSelection:
    """Test device auto-selection priority algorithms."""

    @pytest.mark.asyncio
    async def test_auto_select_device_priority_previous_selection(self):
        """Test priority 1: Previously selected device (lines 105-116)."""
        adb_manager = ADBManager()
        adb_manager.selected_device = "emulator-5556"  # Set previous selection

        with patch.object(adb_manager, "list_devices") as mock_list:
            mock_list.return_value = [
                {"id": "emulator-5554", "status": "device"},
                {"id": "emulator-5556", "status": "device"},  # Previously selected
                {"id": "physical-device", "status": "device"},
            ]

            result = await adb_manager.auto_select_device()

            assert result["success"] is True
            assert result["selected"]["id"] == "emulator-5556"
            assert result["reason"] == "previous_selection"

    @pytest.mark.asyncio
    async def test_auto_select_device_priority_physical_first(self):
        """Test priority 2: First physical device (lines 117-124)."""
        adb_manager = ADBManager()
        adb_manager.selected_device = None  # No previous selection

        with patch.object(adb_manager, "list_devices") as mock_list:
            mock_list.return_value = [
                {"id": "emulator-5554", "status": "device"},
                {"id": "physical-device-1", "status": "device"},  # First physical
                {"id": "physical-device-2", "status": "device"},
                {"id": "emulator-5556", "status": "device"},
            ]

            result = await adb_manager.auto_select_device()

            assert result["success"] is True
            assert result["selected"]["id"] == "physical-device-1"
            assert result["reason"] == "first_physical"
            assert adb_manager.selected_device == "physical-device-1"

    @pytest.mark.asyncio
    async def test_auto_select_device_priority_emulator_fallback(self):
        """Test priority 3: First emulator when no physical devices (lines 126-133)."""
        adb_manager = ADBManager()
        adb_manager.selected_device = None

        with patch.object(adb_manager, "list_devices") as mock_list:
            mock_list.return_value = [
                {"id": "emulator-5554", "status": "device"},  # First emulator
                {"id": "emulator-5556", "status": "device"},
                {"id": "physical-device", "status": "offline"},  # Not available
            ]

            result = await adb_manager.auto_select_device()

            assert result["success"] is True
            assert result["selected"]["id"] == "emulator-5554"
            assert result["reason"] == "first_emulator"
            assert adb_manager.selected_device == "emulator-5554"

    @pytest.mark.asyncio
    async def test_auto_select_device_no_available_devices(self):
        """Test failure when no devices in 'device' status (lines 135-139)."""
        adb_manager = ADBManager()

        with patch.object(adb_manager, "list_devices") as mock_list:
            mock_list.return_value = [
                {"id": "emulator-5554", "status": "offline"},
                {"id": "physical-device", "status": "unauthorized"},
            ]

            result = await adb_manager.auto_select_device()

            assert result["success"] is False
            assert "No devices in 'device' status" in result["error"]
            assert "devices" in result
            assert len(result["devices"]) == 2


class TestADBManagerDeviceListParsing:
    """Test device list parsing edge cases."""

    @pytest.mark.asyncio
    async def test_list_devices_empty_lines_handling(self):
        """Test handling of empty lines in device list (lines 61-62)."""
        adb_manager = ADBManager()

        with patch.object(adb_manager, "execute_adb_command") as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": "List of devices attached\n\nemulator-5554\tdevice\n\n\n",
                "stderr": "",
                "return_code": 0,
            }

            devices = await adb_manager.list_devices()
            assert len(devices) == 1
            assert devices[0]["id"] == "emulator-5554"

    @pytest.mark.asyncio
    async def test_list_devices_malformed_lines_handling(self):
        """Test handling of malformed device lines (lines 65-66)."""
        adb_manager = ADBManager()

        with patch.object(adb_manager, "execute_adb_command") as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": "List of devices attached\nmalformed_line\nemulator-5554\tdevice\nincomplete",
                "stderr": "",
                "return_code": 0,
            }

            devices = await adb_manager.list_devices()
            assert len(devices) == 1
            assert devices[0]["id"] == "emulator-5554"

    @pytest.mark.asyncio
    async def test_list_devices_extended_info_parsing(self):
        """Test parsing of extended device information (lines 73-77)."""
        adb_manager = ADBManager()

        with patch.object(adb_manager, "execute_adb_command") as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": (
                    "List of devices attached\n"
                    "emulator-5554\tdevice product:sdk_gphone_x86 model:Android_SDK_built_for_x86 device:generic_x86 transport_id:1\n"
                ),
                "stderr": "",
                "return_code": 0,
            }

            devices = await adb_manager.list_devices()
            assert len(devices) == 1
            device = devices[0]
            assert device["id"] == "emulator-5554"
            assert device["status"] == "device"
            assert device["product"] == "sdk_gphone_x86"
            assert device["model"] == "Android_SDK_built_for_x86"
            assert device["device"] == "generic_x86"
            assert device["transport_id"] == "1"

    @pytest.mark.asyncio
    async def test_list_devices_exception_handling(self):
        """Test exception handling in list_devices (lines 83-85)."""
        adb_manager = ADBManager()

        with patch.object(adb_manager, "execute_adb_command") as mock_execute:
            mock_execute.side_effect = Exception("Network error")

            devices = await adb_manager.list_devices()
            assert devices == []


class TestADBManagerCommandExecution:
    """Test command execution timeout and error handling."""

    @pytest.mark.asyncio
    async def test_execute_command_with_device_formatting(self):
        """Test command formatting with device ID (lines 157-161)."""
        adb_manager = ADBManager()
        adb_manager.selected_device = "test-device"

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = Mock()
            mock_process.communicate = AsyncMock(return_value=(b"output", b""))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            result = await adb_manager.execute_adb_command(
                "adb -s {device} shell echo test", check_device=False
            )

            assert result["success"] is True
            # Check that the command was formatted with device ID
            mock_subprocess.assert_called_once()
            call_args = mock_subprocess.call_args[0]
            assert "test-device" in " ".join(call_args)

    @pytest.mark.asyncio
    async def test_execute_command_timeout_module_integration(self):
        """Test timeout module integration (lines 175-179)."""
        adb_manager = ADBManager()

        # Mock the timeout module by patching the import
        mock_timeout_module = Mock()
        mock_timeout_module.has_deadline.return_value = True
        mock_timeout_module.remaining_time.return_value = 5.0

        with (
            patch.dict("sys.modules", {"src.timeout": mock_timeout_module}),
            patch("asyncio.create_subprocess_exec") as mock_subprocess,
        ):

            mock_process = Mock()
            mock_process.communicate = AsyncMock(return_value=(b"output", b""))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            result = await adb_manager.execute_adb_command(
                "test command", timeout=30, check_device=False
            )

            assert result["success"] is True
            # The import and usage should work without error
            mock_subprocess.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_command_timeout_exception_fallback(self):
        """Test timeout module exception fallback (lines 178-179)."""
        adb_manager = ADBManager()

        # Mock an import error by removing the module from sys.modules
        with (
            patch.dict("sys.modules", {}, clear=False),
            patch("asyncio.create_subprocess_exec") as mock_subprocess,
        ):

            # Ensure the timeout module import fails
            if "src.timeout" in sys.modules:
                del sys.modules["src.timeout"]

            mock_process = Mock()
            mock_process.communicate = AsyncMock(return_value=(b"output", b""))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            result = await adb_manager.execute_adb_command(
                "test command", timeout=15, check_device=False
            )

            assert result["success"] is True
            # Should fall back to original timeout value

    @pytest.mark.asyncio
    async def test_execute_command_timeout_process_cleanup(self):
        """Test process cleanup on timeout (lines 187-203)."""
        adb_manager = ADBManager()

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = Mock()
            mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
            mock_process.terminate = Mock()
            mock_process.kill = Mock()
            mock_subprocess.return_value = mock_process

            # Patch asyncio.timeout to raise TimeoutError during the execution
            with patch("asyncio.timeout") as mock_timeout:
                mock_timeout.side_effect = asyncio.TimeoutError

                result = await adb_manager.execute_adb_command(
                    "test command", timeout=1, check_device=False
                )

                assert result["success"] is False
                assert "timed out after" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_command_process_lookup_error_handling(self):
        """Test ProcessLookupError handling during cleanup (lines 189-190, 197-198)."""
        adb_manager = ADBManager()

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = Mock()
            mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
            mock_process.terminate = Mock(side_effect=ProcessLookupError)
            mock_process.kill = Mock(side_effect=ProcessLookupError)
            mock_subprocess.return_value = mock_process

            # Use the real timeout context manager that will actually timeout
            with patch("asyncio.timeout") as mock_timeout:
                mock_timeout.side_effect = asyncio.TimeoutError

                result = await adb_manager.execute_adb_command(
                    "test command", timeout=1, check_device=False
                )

                assert result["success"] is False
                assert "timed out" in result["error"]
                # Should handle ProcessLookupError gracefully

    @pytest.mark.asyncio
    async def test_execute_command_cleanup_timeout_handling(self):
        """Test cleanup timeout handling (lines 200-203)."""
        adb_manager = ADBManager()

        with (
            patch("asyncio.create_subprocess_exec") as mock_subprocess,
            patch("asyncio.timeout") as mock_timeout_ctx,
        ):

            mock_process = Mock()
            # First timeout during main execution, second timeout during cleanup
            mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
            mock_process.terminate = Mock()
            mock_process.kill = Mock()
            mock_subprocess.return_value = mock_process

            # Mock timeout context manager
            timeout_calls = 0

            async def mock_timeout_enter():
                nonlocal timeout_calls
                timeout_calls += 1
                if timeout_calls == 1:  # First call (main execution)
                    raise asyncio.TimeoutError
                elif timeout_calls == 2:  # Second call (cleanup)
                    raise asyncio.TimeoutError
                # Third call should succeed (return normally)
                return None

            mock_timeout_instance = Mock()
            mock_timeout_instance.__aenter__ = AsyncMock(side_effect=mock_timeout_enter)
            mock_timeout_instance.__aexit__ = AsyncMock(return_value=None)
            mock_timeout_ctx.return_value = mock_timeout_instance

            result = await adb_manager.execute_adb_command(
                "test command", timeout=1, check_device=False
            )

            assert result["success"] is False
            assert "timed out" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_command_general_exception_handling(self):
        """Test general exception handling (lines 217-222)."""
        adb_manager = ADBManager()

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_subprocess.side_effect = OSError("Permission denied")

            result = await adb_manager.execute_adb_command(
                "test command", check_device=False
            )

            assert result["success"] is False
            assert "Command execution failed" in result["error"]
            assert "Permission denied" in result["error"]


class TestADBManagerDeviceHealth:
    """Test device health checking mechanisms."""

    @pytest.mark.asyncio
    async def test_check_device_health_no_device_selected(self):
        """Test health check with no device selected (lines 228-230)."""
        adb_manager = ADBManager()
        adb_manager.selected_device = None

        result = await adb_manager.check_device_health()

        assert result["success"] is False
        assert "No device selected" in result["error"]

    @pytest.mark.asyncio
    async def test_check_device_health_comprehensive_checks(self):
        """Test comprehensive health checks with various results."""
        adb_manager = ADBManager()
        device_id = "test-device"

        # Mock different check results - need to make sure connectivity check actually contains 'connected'
        health_responses = [
            {"success": True, "stdout": "connected", "stderr": ""},  # connectivity
            {
                "success": True,
                "stdout": "Display Power: state=ON connected",
                "stderr": "",
            },  # screen_state (also contains connected)
            {
                "success": True,
                "stdout": "Service uiautomator: found connected",
                "stderr": "",
            },  # ui_service (also contains connected)
        ]

        with patch.object(adb_manager, "execute_adb_command") as mock_execute:
            mock_execute.side_effect = health_responses

            result = await adb_manager.check_device_health(device_id)

            assert result["success"] is True
            assert result["healthy"] is True
            assert result["device_id"] == device_id
            assert "checks" in result
            assert len(result["checks"]) == 3

            # Verify all checks passed
            for check_name, check_result in result["checks"].items():
                assert check_result["passed"] is True

    @pytest.mark.asyncio
    async def test_check_device_health_failed_checks(self):
        """Test health checks with some failures."""
        adb_manager = ADBManager()
        device_id = "test-device"

        # Mock mixed check results
        health_responses = [
            {
                "success": False,
                "stdout": "",
                "stderr": "connection failed",
            },  # connectivity failed
            {
                "success": True,
                "stdout": "Display Power: state=ON",
                "stderr": "",
            },  # screen_state ok
            {
                "success": True,
                "stdout": "Service uiautomator: not found",
                "stderr": "",
            },  # ui_service failed
        ]

        with patch.object(adb_manager, "execute_adb_command") as mock_execute:
            mock_execute.side_effect = health_responses

            result = await adb_manager.check_device_health(device_id)

            assert result["success"] is True
            assert result["healthy"] is False  # Overall health should be false
            assert result["device_id"] == device_id


class TestADBManagerDeviceInfo:
    """Test device information retrieval and parsing."""

    @pytest.mark.asyncio
    async def test_get_device_info_no_device_selected(self):
        """Test device info with no device selected (lines 264-266)."""
        adb_manager = ADBManager()
        adb_manager.selected_device = None

        result = await adb_manager.get_device_info()

        assert result["success"] is False
        assert "No device selected" in result["error"]

    @pytest.mark.asyncio
    async def test_get_device_info_property_parsing(self):
        """Test device property parsing (lines 277-301)."""
        adb_manager = ADBManager()
        device_id = "test-device"

        # Mock getprop output with various property formats
        mock_stdout = """[ro.product.model]: [Test Device]
[ro.product.manufacturer]: [Test Manufacturer]
[ro.build.version.release]: [13]
[ro.build.version.sdk]: [33]
[ro.serialno]: [test-serial-123]
[invalid.property.format]: incomplete
[another.prop]: [value with spaces and symbols!@#]
not a property line
[empty.prop]: []"""

        with patch.object(adb_manager, "execute_adb_command") as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": mock_stdout,
                "stderr": "",
                "return_code": 0,
            }

            result = await adb_manager.get_device_info(device_id)

            assert result["success"] is True
            device_info = result["device_info"]
            assert device_info["device_id"] == device_id
            assert device_info["model"] == "Test Device"
            assert device_info["manufacturer"] == "Test Manufacturer"
            assert device_info["android_version"] == "13"
            assert device_info["api_level"] == "33"
            assert device_info["serial"] == "test-serial-123"

            # Check that properties with spaces are handled correctly
            assert (
                device_info["all_properties"]["another.prop"]
                == "value with spaces and symbols!@#"
            )
            assert device_info["all_properties"]["empty.prop"] == ""

    @pytest.mark.asyncio
    async def test_get_device_info_missing_properties(self):
        """Test handling of missing standard properties."""
        adb_manager = ADBManager()
        device_id = "test-device"

        # Mock getprop output with missing standard properties
        mock_stdout = """[some.other.prop]: [value]
[ro.build.type]: [user]"""

        with patch.object(adb_manager, "execute_adb_command") as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": mock_stdout,
                "stderr": "",
                "return_code": 0,
            }

            result = await adb_manager.get_device_info(device_id)

            assert result["success"] is True
            device_info = result["device_info"]
            # Should use "Unknown" for missing properties
            assert device_info["model"] == "Unknown"
            assert device_info["manufacturer"] == "Unknown"
            assert device_info["android_version"] == "Unknown"
            assert device_info["api_level"] == "Unknown"
            assert device_info["serial"] == device_id  # Falls back to device_id

    @pytest.mark.asyncio
    async def test_get_device_info_exception_handling(self):
        """Test exception handling in get_device_info (lines 305-306)."""
        adb_manager = ADBManager()
        device_id = "test-device"

        with patch.object(adb_manager, "execute_adb_command") as mock_execute:
            mock_execute.side_effect = Exception("Connection error")

            result = await adb_manager.get_device_info(device_id)

            assert result["success"] is False
            assert "Failed to get device info" in result["error"]
            assert "Connection error" in result["error"]


class TestADBManagerScreenSize:
    """Test screen size detection and parsing."""

    @pytest.mark.asyncio
    async def test_get_screen_size_no_device_selected(self):
        """Test screen size with no device selected (lines 310-312)."""
        adb_manager = ADBManager()
        adb_manager.selected_device = None

        result = await adb_manager.get_screen_size()

        assert result["success"] is False
        assert "No device selected" in result["error"]

    @pytest.mark.asyncio
    async def test_get_screen_size_parsing_success(self):
        """Test successful screen size parsing (lines 322-333)."""
        adb_manager = ADBManager()
        device_id = "test-device"

        test_cases = [
            ("Physical size: 1080x1920", 1080, 1920),
            ("Override size: 720x1280", 720, 1280),
            ("Size: 1440x2560", 1440, 2560),
        ]

        for output, expected_width, expected_height in test_cases:
            with patch.object(adb_manager, "execute_adb_command") as mock_execute:
                mock_execute.return_value = {
                    "success": True,
                    "stdout": output,
                    "stderr": "",
                    "return_code": 0,
                }

                result = await adb_manager.get_screen_size(device_id)

                assert result["success"] is True
                assert result["width"] == expected_width
                assert result["height"] == expected_height
                assert result["raw_output"] == output

    @pytest.mark.asyncio
    async def test_get_screen_size_parsing_failure(self):
        """Test screen size parsing failure (lines 335-335)."""
        adb_manager = ADBManager()
        device_id = "test-device"

        test_cases = [
            "Invalid output format",
            "Size info not available",
            "No colon in output",
        ]

        for invalid_output in test_cases:
            with patch.object(adb_manager, "execute_adb_command") as mock_execute:
                mock_execute.return_value = {
                    "success": True,
                    "stdout": invalid_output,
                    "stderr": "",
                    "return_code": 0,
                }

                result = await adb_manager.get_screen_size(device_id)

                assert result["success"] is False
                assert (
                    "Could not parse screen size" in result["error"]
                    or "Failed to get screen size" in result["error"]
                )
                assert invalid_output in result["error"]

    @pytest.mark.asyncio
    async def test_get_screen_size_exception_handling(self):
        """Test exception handling in get_screen_size (lines 337-338)."""
        adb_manager = ADBManager()
        device_id = "test-device"

        with patch.object(adb_manager, "execute_adb_command") as mock_execute:
            mock_execute.side_effect = Exception("Network timeout")

            result = await adb_manager.get_screen_size(device_id)

            assert result["success"] is False
            assert "Failed to get screen size" in result["error"]
            assert "Network timeout" in result["error"]


class TestADBManagerForegroundApp:
    """Test foreground app detection with multiple command fallbacks."""

    @pytest.mark.asyncio
    async def test_get_foreground_app_no_device_selected(self):
        """Test foreground app with no device selected (lines 347-349)."""
        adb_manager = ADBManager()
        adb_manager.selected_device = None

        result = await adb_manager.get_foreground_app()

        assert result["success"] is False
        assert "No device selected" in result["error"]

    @pytest.mark.asyncio
    async def test_get_foreground_app_mCurrentFocus_format(self):
        """Test parsing mCurrentFocus format (lines 359-382)."""
        adb_manager = ADBManager()
        device_id = "test-device"

        mock_outputs = [
            # First command succeeds with mCurrentFocus format
            {
                "success": True,
                "stdout": "mCurrentFocus=Window{12345 u0 com.example.app/com.example.MainActivity t1}",
                "stderr": "",
            }
        ]

        with patch.object(adb_manager, "execute_adb_command") as mock_execute:
            mock_execute.side_effect = mock_outputs

            result = await adb_manager.get_foreground_app(device_id)

            assert result["success"] is True
            assert result["package"] == "com.example.app"
            assert result["activity"] == "com.example.MainActivity"
            assert "mCurrentFocus" in result["source"]
            assert "com.example.app/com.example.MainActivity" in result["raw"]

    @pytest.mark.asyncio
    async def test_get_foreground_app_mResumedActivity_format(self):
        """Test parsing mResumedActivity format."""
        adb_manager = ADBManager()
        device_id = "test-device"

        mock_outputs = [
            # First command fails
            {"success": False, "stdout": "", "stderr": "error"},
            # Second command succeeds with mResumedActivity format
            {
                "success": True,
                "stdout": "mResumedActivity: ActivityRecord{67890 u0 com.test.browser/com.test.BrowserActivity t123}",
                "stderr": "",
            },
        ]

        with patch.object(adb_manager, "execute_adb_command") as mock_execute:
            mock_execute.side_effect = mock_outputs

            result = await adb_manager.get_foreground_app(device_id)

            assert result["success"] is True
            assert result["package"] == "com.test.browser"
            assert result["activity"] == "com.test.BrowserActivity"
            assert "mResumedActivity" in result["source"]

    @pytest.mark.asyncio
    async def test_get_foreground_app_fallback_commands(self):
        """Test fallback to third command when first two fail."""
        adb_manager = ADBManager()
        device_id = "test-device"

        mock_outputs = [
            # First two commands fail
            {"success": False, "stdout": "", "stderr": "error1"},
            {"success": False, "stdout": "", "stderr": "error2"},
            # Third command succeeds
            {
                "success": True,
                "stdout": "some other format with com.final.app/com.final.FinalActivity in it",
                "stderr": "",
            },
        ]

        with patch.object(adb_manager, "execute_adb_command") as mock_execute:
            mock_execute.side_effect = mock_outputs

            result = await adb_manager.get_foreground_app(device_id)

            assert result["success"] is True
            assert result["package"] == "com.final.app"
            assert result["activity"] == "com.final.FinalActivity"

    @pytest.mark.asyncio
    async def test_get_foreground_app_no_match_found(self):
        """Test when no package/activity pattern is found (lines 386)."""
        adb_manager = ADBManager()
        device_id = "test-device"

        mock_outputs = [
            {"success": True, "stdout": "no package info here", "stderr": ""},
            {"success": True, "stdout": "also no package info", "stderr": ""},
            {"success": True, "stdout": "still no package info", "stderr": ""},
        ]

        with patch.object(adb_manager, "execute_adb_command") as mock_execute:
            mock_execute.side_effect = mock_outputs

            result = await adb_manager.get_foreground_app(device_id)

            assert result["success"] is False
            assert "Unable to detect foreground app" in result["error"]

    @pytest.mark.asyncio
    async def test_get_foreground_app_exception_handling(self):
        """Test exception handling in command execution (lines 383-384)."""
        adb_manager = ADBManager()
        device_id = "test-device"

        with patch.object(adb_manager, "execute_adb_command") as mock_execute:
            # All commands raise exceptions
            mock_execute.side_effect = Exception("Connection error")

            result = await adb_manager.get_foreground_app(device_id)

            assert result["success"] is False
            assert "Unable to detect foreground app" in result["error"]

    @pytest.mark.asyncio
    async def test_get_foreground_app_complex_activity_parsing(self):
        """Test parsing complex activity names with multiple tokens."""
        adb_manager = ADBManager()
        device_id = "test-device"

        # Test case with complex output where activity extraction is challenging
        complex_output = "mCurrentFocus=Window{abc123 u0 com.complex.app/com.complex.deep.nested.VeryLongActivityName t456} other_data"

        mock_outputs = [{"success": True, "stdout": complex_output, "stderr": ""}]

        with patch.object(adb_manager, "execute_adb_command") as mock_execute:
            mock_execute.side_effect = mock_outputs

            result = await adb_manager.get_foreground_app(device_id)

            assert result["success"] is True
            assert result["package"] == "com.complex.app"
            assert result["activity"] == "com.complex.deep.nested.VeryLongActivityName"

    @pytest.mark.asyncio
    async def test_get_foreground_app_custom_timeout(self):
        """Test custom timeout parameter."""
        adb_manager = ADBManager()
        device_id = "test-device"

        with patch.object(adb_manager, "execute_adb_command") as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": "mCurrentFocus=Window{123 u0 com.test.app/com.test.Activity}",
                "stderr": "",
            }

            result = await adb_manager.get_foreground_app(device_id, timeout=15)

            assert result["success"] is True
            # Verify timeout was passed to execute_adb_command
            mock_execute.assert_called_with(
                mock_execute.call_args[0][0], timeout=15, check_device=False
            )


class TestADBManagerCacheAndState:
    """Test caching mechanisms and state management."""

    @pytest.mark.asyncio
    async def test_device_cache_initialization(self):
        """Test initial cache state."""
        adb_manager = ADBManager()

        assert adb_manager.devices_cache == {}
        assert adb_manager._last_device_check is None
        assert adb_manager._device_cache_ttl == 30

    @pytest.mark.asyncio
    async def test_selected_device_persistence(self):
        """Test that selected device persists across operations."""
        adb_manager = ADBManager()
        adb_manager.selected_device = "persistent-device"

        # The device should remain selected
        assert adb_manager.selected_device == "persistent-device"

        # Should be used in commands that support device formatting
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = Mock()
            mock_process.communicate = AsyncMock(return_value=(b"output", b""))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            await adb_manager.execute_adb_command(
                "adb -s {device} shell echo test", check_device=False
            )

            # Verify device was used in command
            call_args = mock_subprocess.call_args[0]
            assert "persistent-device" in " ".join(call_args)


class TestADBManagerIntegration:
    """Integration tests for multiple components working together."""

    @pytest.mark.asyncio
    async def test_full_device_workflow(self):
        """Test complete device selection and info retrieval workflow."""
        adb_manager = ADBManager()

        # Mock device list with multiple devices
        devices_output = (
            "List of devices attached\n"
            "emulator-5554\tdevice\n"
            "physical-device\tdevice\n"
        )

        # Mock device properties
        properties_output = (
            "[ro.product.model]: [Test Phone]\n"
            "[ro.product.manufacturer]: [TestCorp]\n"
            "[ro.build.version.release]: [12]\n"
            "[ro.build.version.sdk]: [31]\n"
        )

        # Mock screen size
        screen_output = "Physical size: 1080x2340"

        with patch.object(adb_manager, "execute_adb_command") as mock_execute:
            # Set up responses for different commands
            def command_response(command, **kwargs):
                if "devices -l" in command:
                    return {
                        "success": True,
                        "stdout": devices_output,
                        "stderr": "",
                        "return_code": 0,
                    }
                elif "getprop" in command:
                    return {
                        "success": True,
                        "stdout": properties_output,
                        "stderr": "",
                        "return_code": 0,
                    }
                elif "wm size" in command:
                    return {
                        "success": True,
                        "stdout": screen_output,
                        "stderr": "",
                        "return_code": 0,
                    }
                else:
                    return {
                        "success": True,
                        "stdout": "ok",
                        "stderr": "",
                        "return_code": 0,
                    }

            mock_execute.side_effect = command_response

            # Test workflow
            devices = await adb_manager.list_devices()
            assert len(devices) == 2

            selection_result = await adb_manager.auto_select_device()
            assert selection_result["success"] is True
            assert (
                selection_result["selected"]["id"] == "physical-device"
            )  # Physical device has priority

            device_info_result = await adb_manager.get_device_info()
            assert device_info_result["success"] is True
            assert device_info_result["device_info"]["model"] == "Test Phone"

            screen_result = await adb_manager.get_screen_size()
            assert screen_result["success"] is True
            assert screen_result["width"] == 1080
            assert screen_result["height"] == 2340

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """Test error recovery across multiple operations."""
        adb_manager = ADBManager()

        # Test no devices scenario separately
        with patch.object(adb_manager, "list_devices", return_value=[]):
            devices = await adb_manager.list_devices()
            assert len(devices) == 0

            selection_result = await adb_manager.auto_select_device()
            assert selection_result["success"] is False
            assert "No Android devices connected" in selection_result["error"]

        # Test device available scenario
        with patch.object(
            adb_manager,
            "list_devices",
            return_value=[{"id": "emulator-5554", "status": "device"}],
        ):
            devices = await adb_manager.list_devices()
            assert len(devices) == 1

            selection_result = await adb_manager.auto_select_device()
            assert selection_result["success"] is True
            assert selection_result["selected"]["id"] == "emulator-5554"
