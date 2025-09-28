"""Tests for ADB Manager functionality."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, Mock
from datetime import datetime, timedelta

from src.adb_manager import ADBManager, ADBCommands
from tests.mocks import MockADBCommand, MockDeviceScenarios, MockErrorScenarios


class TestADBManager:
    """Test ADB Manager device operations."""

    @pytest.mark.asyncio
    async def test_list_devices_success(self, mock_adb_manager):
        """Test successful device listing."""
        devices = await mock_adb_manager.list_devices()

        assert len(devices) >= 1
        device = devices[0]
        assert "id" in device
        assert "status" in device
        assert device["status"] == "device"

    @pytest.mark.asyncio
    async def test_list_devices_no_devices(self):
        """Test device listing when no devices connected."""
        adb_manager = ADBManager()

        with patch.object(adb_manager, 'execute_adb_command') as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": "List of devices attached\n\n",
                "stderr": "",
                "return_code": 0
            }

            devices = await adb_manager.list_devices()
            assert devices == []

    @pytest.mark.asyncio
    async def test_auto_select_device_success(self, mock_adb_manager):
        """Test successful automatic device selection."""
        result = await mock_adb_manager.auto_select_device()

        assert result["success"] is True
        assert "selected" in result
        assert result["selected"]["id"] is not None
        assert "health" in result

    @pytest.mark.asyncio
    async def test_auto_select_device_no_devices(self):
        """Test auto-select when no devices available."""
        adb_manager = ADBManager()

        with patch.object(adb_manager, 'list_devices') as mock_list:
            mock_list.return_value = []

            result = await adb_manager.auto_select_device()
            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_device_info_success(self, mock_adb_manager):
        """Test successful device info retrieval."""
        result = await mock_adb_manager.get_device_info()

        assert result["success"] is True
        assert "device_info" in result

    @pytest.mark.asyncio
    async def test_get_screen_size(self, mock_adb_manager):
        """Test screen size retrieval."""
        screen_size = await mock_adb_manager.get_screen_size()

        assert "width" in screen_size
        assert "height" in screen_size
        assert screen_size["width"] > 0
        assert screen_size["height"] > 0

    @pytest.mark.asyncio
    async def test_check_device_health(self, mock_adb_manager):
        """Test device health check."""
        health = await mock_adb_manager.check_device_health()

        assert "status" in health
        assert health["status"] in ["healthy", "degraded", "unhealthy"]
        assert "battery_level" in health

    @pytest.mark.asyncio
    async def test_execute_adb_command_timeout(self):
        """Test ADB command timeout handling."""
        adb_manager = ADBManager()
        adb_manager.selected_device = "mock-device"  # Set device to skip auto-selection

        # Mock asyncio.timeout to simulate a timeout during process communication
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def fake_timeout(_):
            # Simulate timeout on entering the context
            raise asyncio.TimeoutError
            yield  # unreachable, ensures valid async contextmanager signature

        with patch('asyncio.timeout', fake_timeout):
            result = await adb_manager.execute_adb_command(
                "test command", timeout=1, check_device=False
            )

            assert result["success"] is False
            assert "timeout" in result["error"].lower() or "timed out" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_adb_command_success(self):
        """Test successful ADB command execution."""
        adb_manager = ADBManager()

        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # Mock successful process
            mock_process = Mock()
            mock_process.communicate = AsyncMock(return_value=(b"success output", b""))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            result = await adb_manager.execute_adb_command("test command", check_device=False)

            assert result["success"] is True
            assert result["stdout"] == "success output"
            assert result["returncode"] == 0

    @pytest.mark.asyncio
    async def test_execute_adb_command_failure(self):
        """Test failed ADB command execution."""
        adb_manager = ADBManager()

        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # Mock failed process
            mock_process = Mock()
            mock_process.communicate = AsyncMock(return_value=(b"", b"error output"))
            mock_process.returncode = 1
            mock_subprocess.return_value = mock_process

            result = await adb_manager.execute_adb_command("test command", check_device=False)

            assert result["success"] is False
            assert result["stderr"] == "error output"
            assert result["returncode"] == 1

    @pytest.mark.asyncio
    async def test_device_cache_functionality(self, mock_adb_manager):
        """Test device information caching."""
        # First call should populate cache
        result1 = await mock_adb_manager.list_devices()

        # Second call should use cache (if implemented)
        result2 = await mock_adb_manager.list_devices()

        assert result1 == result2

    @pytest.mark.asyncio
    async def test_device_selection_validation(self):
        """Test device selection with invalid device ID."""
        adb_manager = ADBManager()

        with patch.object(adb_manager, 'list_devices') as mock_list:
            mock_list.return_value = [{"id": "emulator-5554", "status": "device"}]

            # Try to select non-existent device
            adb_manager.selected_device = "invalid-device-id"

            # Device health check should fail for invalid device
            with patch.object(adb_manager, 'execute_adb_command') as mock_execute:
                mock_execute.return_value = MockErrorScenarios.device_not_found_error()

                health = await adb_manager.check_device_health("invalid-device-id")
                # This should handle the error gracefully


class TestADBCommands:
    """Test ADB command string formatting."""

    def test_devices_list_command(self):
        """Test devices list command format."""
        assert ADBCommands.DEVICES_LIST == "adb devices -l"

    def test_device_info_command_formatting(self):
        """Test device info command formatting."""
        device_id = "emulator-5554"
        expected = f"adb -s {device_id} shell getprop"
        assert ADBCommands.DEVICE_INFO.format(device=device_id) == expected

    def test_ui_dump_commands(self):
        """Test UI dump command variations."""
        device_id = "test-device"

        normal_dump = ADBCommands.UI_DUMP.format(device=device_id)
        compressed_dump = ADBCommands.UI_DUMP_COMPRESSED.format(device=device_id)

        assert "uiautomator dump" in normal_dump
        assert "--compressed" in compressed_dump

    def test_input_commands_formatting(self):
        """Test input command formatting."""
        device_id = "test-device"

        tap_cmd = ADBCommands.TAP.format(device=device_id, x=100, y=200)
        assert "input tap 100 200" in tap_cmd

        swipe_cmd = ADBCommands.SWIPE.format(
            device=device_id, x1=100, y1=200, x2=300, y2=400, duration=500
        )
        assert "input swipe 100 200 300 400 500" in swipe_cmd

        text_cmd = ADBCommands.TEXT_INPUT.format(device=device_id, text="test")
        assert "input text test" in text_cmd

    def test_media_commands_formatting(self):
        """Test media capture command formatting."""
        device_id = "test-device"

        screenshot_cmd = ADBCommands.SCREENSHOT.format(device=device_id)
        assert "screencap -p" in screenshot_cmd

        record_cmd = ADBCommands.SCREEN_RECORD.format(
            device=device_id, options="--time-limit 60", path="/sdcard/test.mp4"
        )
        assert "screenrecord --time-limit 60 /sdcard/test.mp4" in record_cmd


class TestADBManagerErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_handle_device_offline(self):
        """Test handling offline device scenario."""
        adb_manager = ADBManager()

        with patch.object(adb_manager, 'execute_adb_command') as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": "List of devices attached\nemulator-5554\toffline\n",
                "stderr": "",
                "return_code": 0
            }

            devices = await adb_manager.list_devices()
            offline_device = next((d for d in devices if d["status"] == "offline"), None)
            assert offline_device is not None

    @pytest.mark.asyncio
    async def test_handle_unauthorized_device(self):
        """Test handling unauthorized device scenario."""
        adb_manager = ADBManager()

        with patch.object(adb_manager, 'execute_adb_command') as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "stdout": "List of devices attached\nemulator-5554\tunauthorized\n",
                "stderr": "",
                "return_code": 0
            }

            devices = await adb_manager.list_devices()
            unauthorized_device = next(
                (d for d in devices if d["status"] == "unauthorized"), None
            )
            assert unauthorized_device is not None

    @pytest.mark.asyncio
    async def test_handle_adb_daemon_error(self):
        """Test handling ADB daemon errors."""
        adb_manager = ADBManager()

        with patch.object(adb_manager, 'execute_adb_command') as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "stdout": "",
                "stderr": "adb: daemon not running",
                "return_code": 1,
                "error": "ADB daemon not running"
            }

            devices = await adb_manager.list_devices()
            assert devices == []

    @pytest.mark.asyncio
    async def test_handle_command_permission_denied(self):
        """Test handling permission denied errors."""
        adb_manager = ADBManager()
        adb_manager.selected_device = "emulator-5554"

        with patch.object(adb_manager, 'execute_adb_command') as mock_execute:
            mock_execute.return_value = MockErrorScenarios.permission_denied_error()

            result = await adb_manager.get_device_info()
            assert result["success"] is False
            assert "permission" in result["error"].lower()


class TestADBManagerPerformance:
    """Test performance-related functionality."""

    @pytest.mark.asyncio
    async def test_concurrent_command_execution(self, mock_adb_manager):
        """Test concurrent ADB command execution."""
        # Execute multiple commands concurrently
        tasks = [
            mock_adb_manager.get_device_info(),
            mock_adb_manager.check_device_health(),
            mock_adb_manager.get_screen_size()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All commands should complete successfully
        for result in results:
            assert not isinstance(result, Exception)

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_command_timeout_behavior(self):
        """Test command timeout behavior with various timeout values."""
        adb_manager = ADBManager()

        # Test with very short timeout
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def fake_timeout(_):
            # Simulate timeout on entering the context
            raise asyncio.TimeoutError
            yield

        with patch('asyncio.timeout', fake_timeout):
            result = await adb_manager.execute_adb_command(
                "test command", timeout=0.001
            )
            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_device_cache_expiration(self):
        """Test device cache expiration logic."""
        adb_manager = ADBManager()

        # Set cache TTL to very short value for testing
        original_ttl = adb_manager._device_cache_ttl
        adb_manager._device_cache_ttl = 0.1  # 0.1 seconds

        try:
            with patch.object(adb_manager, 'execute_adb_command') as mock_execute:
                mock_execute.return_value = {
                    "success": True,
                    "stdout": "List of devices attached\nemulator-5554\tdevice\n",
                    "stderr": "",
                    "return_code": 0
                }

                # First call
                devices1 = await adb_manager.list_devices()

                # Wait for cache to expire
                await asyncio.sleep(0.2)

                # Second call should refresh cache
                devices2 = await adb_manager.list_devices()

                # Should have been called twice due to cache expiration
                assert mock_execute.call_count >= 2

        finally:
            adb_manager._device_cache_ttl = original_ttl
