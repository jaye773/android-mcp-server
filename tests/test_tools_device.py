"""Dedicated unit tests for src/tools/device.py.

Covers:
  - get_devices: happy path, missing component, exception
  - select_device: happy path with ID, auto-select (no ID), missing component, exception
  - get_device_info: happy path, missing component, exception
  - register_device_tools wiring
"""

import pytest
from unittest.mock import MagicMock

from src.tools.device import (
    get_devices,
    get_device_info,
    register_device_tools,
    select_device,
)
from src.tool_models import DeviceSelectionParams
from src.registry import ComponentRegistry


@pytest.fixture(autouse=True)
def _clean_registry():
    """Ensure a fresh registry for every test."""
    ComponentRegistry.reset()
    yield
    ComponentRegistry.reset()


# ---------------------------------------------------------------------------
# get_devices
# ---------------------------------------------------------------------------


class TestGetDevices:
    @pytest.mark.asyncio
    async def test_happy_path(self, mock_adb_manager):
        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
        mock_adb_manager.list_devices.return_value = [
            {"id": "emu-5554", "status": "device"}
        ]

        result = await get_devices()

        assert result["success"] is True
        assert result["count"] == 1
        assert result["devices"][0]["id"] == "emu-5554"
        mock_adb_manager.list_devices.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_empty_device_list(self, mock_adb_manager):
        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
        mock_adb_manager.list_devices.return_value = []

        result = await get_devices()

        assert result["success"] is True
        assert result["count"] == 0
        assert result["devices"] == []

    @pytest.mark.asyncio
    async def test_missing_component(self):
        """No adb_manager registered -> error response."""
        result = await get_devices()

        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_exception_propagation(self, mock_adb_manager):
        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
        mock_adb_manager.list_devices.side_effect = RuntimeError("adb crashed")

        result = await get_devices()

        assert result["success"] is False
        assert "adb crashed" in result["error"]


# ---------------------------------------------------------------------------
# select_device
# ---------------------------------------------------------------------------


class TestSelectDevice:
    @pytest.mark.asyncio
    async def test_select_by_id(self, mock_adb_manager):
        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
        mock_adb_manager.select_device.return_value = {
            "success": True,
            "device_id": "emu-5554",
            "state": "device",
        }
        mock_adb_manager.check_device_health.return_value = {"status": "healthy"}

        params = DeviceSelectionParams(device_id="emu-5554")
        result = await select_device(params)

        assert result["success"] is True
        assert result["selected_device"] == "emu-5554"
        assert result["state"] == "device"
        assert result["health"]["status"] == "healthy"
        mock_adb_manager.select_device.assert_awaited_once_with("emu-5554")

    @pytest.mark.asyncio
    async def test_select_by_id_rejected_by_manager(self, mock_adb_manager):
        """If manager rejects the device, the tool surfaces the failure without
        calling health check."""
        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
        mock_adb_manager.select_device.return_value = {
            "success": False,
            "error": "Device 'emu-9999' is not connected",
            "device_id": "emu-9999",
            "state": "not-found",
        }

        params = DeviceSelectionParams(device_id="emu-9999")
        result = await select_device(params)

        assert result["success"] is False
        assert result["state"] == "not-found"
        assert result["device_id"] == "emu-9999"
        mock_adb_manager.check_device_health.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_select(self, mock_adb_manager):
        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
        mock_adb_manager.auto_select_device.return_value = {
            "success": True,
            "selected": {"id": "auto-dev"},
        }

        params = DeviceSelectionParams()  # no device_id
        result = await select_device(params)

        assert result["success"] is True
        mock_adb_manager.auto_select_device.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_missing_component(self):
        params = DeviceSelectionParams(device_id="emu-5554")
        result = await select_device(params)

        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_exception_propagation(self, mock_adb_manager):
        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
        mock_adb_manager.select_device.return_value = {"success": True, "state": "device"}
        mock_adb_manager.check_device_health.side_effect = RuntimeError("health check fail")

        params = DeviceSelectionParams(device_id="emu-5554")
        result = await select_device(params)

        assert result["success"] is False
        assert "health check fail" in result["error"]


# ---------------------------------------------------------------------------
# get_device_info
# ---------------------------------------------------------------------------


class TestGetDeviceInfo:
    @pytest.mark.asyncio
    async def test_happy_path(self, mock_adb_manager):
        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
        mock_adb_manager.get_device_info.return_value = {
            "success": True,
            "device_info": {"model": "Pixel"},
        }
        mock_adb_manager.get_screen_size.return_value = {"width": 1080, "height": 1920}
        mock_adb_manager.check_device_health.return_value = {"status": "healthy"}

        result = await get_device_info()

        assert result["success"] is True
        assert result["device_info"]["model"] == "Pixel"
        assert result["screen_size"]["width"] == 1080
        assert result["health"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_missing_component(self):
        result = await get_device_info()

        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_exception_propagation(self, mock_adb_manager):
        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
        mock_adb_manager.get_device_info.side_effect = RuntimeError("info fail")

        result = await get_device_info()

        assert result["success"] is False
        assert "info fail" in result["error"]

    @pytest.mark.asyncio
    async def test_get_device_info_fails_on_offline(self, mock_adb_manager):
        """When adb getprop fails (device offline), top-level success must be False."""
        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
        mock_adb_manager.get_device_info.return_value = {
            "success": False,
            "error": "device offline",
        }
        mock_adb_manager.get_screen_size.return_value = {
            "success": False,
            "error": "device offline",
        }
        mock_adb_manager.check_device_health.return_value = {
            "success": True,
            "healthy": False,
        }

        result = await get_device_info()

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_device_info_fails_when_model_missing(self, mock_adb_manager):
        """Even if adb returns success, a missing model is a critical failure."""
        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
        mock_adb_manager.get_device_info.return_value = {
            "success": True,
            "device_info": {
                "device_id": "emulator-5554",
                "model": "Unknown",
            },
        }
        mock_adb_manager.get_screen_size.return_value = {"width": 0, "height": 0}
        mock_adb_manager.check_device_health.return_value = {"success": True}

        result = await get_device_info()

        assert result["success"] is False
        assert "model" in result["error"].lower()


# ---------------------------------------------------------------------------
# register_device_tools
# ---------------------------------------------------------------------------


class TestRegisterDeviceTools:
    def test_registers_three_tools(self):
        mcp = MagicMock()
        # mcp.tool() returns a decorator, which is then called with the fn
        mcp.tool.return_value = lambda fn: fn

        register_device_tools(mcp)

        assert mcp.tool.call_count == 3
