"""Device management tools for MCP server."""

import logging
from typing import Any, Dict

from ..decorators import timeout_wrapper
from ..registry import ComponentRegistry
from ..tool_models import DeviceSelectionParams

logger = logging.getLogger(__name__)


@timeout_wrapper()
async def get_devices() -> Dict[str, Any]:
    """List connected Android devices.

    When to use:
    - First step to discover devices before selecting one.
    - If other tools report "No device selected" or device issues.

    Common combos:
    - `get_devices` → `select_device` → `get_device_info`.
    """
    try:
        adb_manager = ComponentRegistry.instance().get("adb_manager")
        if not adb_manager:
            return {
                "success": False,
                "error": "ADB manager not initialized",
            }

        devices = await adb_manager.list_devices()
        return {"success": True, "devices": devices, "count": len(devices)}
    except Exception as e:
        logger.error(f"Get devices failed: {e}")
        return {"success": False, "error": str(e)}


@timeout_wrapper()
async def select_device(params: DeviceSelectionParams) -> Dict[str, Any]:
    """Select Android device to target.

    When to use:
    - After listing devices, or whenever you want to switch targets.

    Tips:
    - Omit `device_id` to auto-select the first healthy device.
    - Use `get_devices` to find valid IDs.

    Common combos:
    - `get_devices` → `select_device` → `get_device_info` → actions (tap/swipe/etc.).
    """
    try:
        adb_manager = ComponentRegistry.instance().get("adb_manager")
        if not adb_manager:
            return {
                "success": False,
                "error": "ADB manager not initialized",
            }

        if params.device_id:
            # Device ID format validation (max_length, pattern) handled by Pydantic
            adb_manager.selected_device = params.device_id
            health = await adb_manager.check_device_health(params.device_id)

            return {
                "success": True,
                "selected_device": params.device_id,
                "health": health,
            }
        else:
            # Auto-select first device
            result = await adb_manager.auto_select_device()
            return result

    except Exception as e:
        logger.error(f"Select device failed: {e}")
        return {"success": False, "error": str(e)}


@timeout_wrapper()
async def get_device_info() -> Dict[str, Any]:
    """Get detailed information about the selected device.

    When to use:
    - Validate connection and capabilities before automation.
    - Size-aware gestures (e.g., directional swipes) depend on screen size.

    Common combos:
    - `select_device` → `get_device_info` → `swipe_direction` or UI actions.
    """
    try:
        adb_manager = ComponentRegistry.instance().get("adb_manager")
        if not adb_manager:
            return {
                "success": False,
                "error": "ADB manager not initialized",
            }

        device_info = await adb_manager.get_device_info()
        screen_size = await adb_manager.get_screen_size()
        health = await adb_manager.check_device_health()

        return {
            "success": True,
            "device_info": device_info.get("device_info"),
            "screen_size": screen_size,
            "health": health,
        }

    except Exception as e:
        logger.error(f"Get device info failed: {e}")
        return {"success": False, "error": str(e)}


def register_device_tools(mcp):
    """Register device management tools with the MCP server.

    Args:
        mcp: FastMCP server instance
    """
    # Register tools with MCP
    mcp.tool(description="List connected Android devices and basic status via ADB.")(
        get_devices
    )
    mcp.tool(
        description="Select a specific device by ID or auto-select the first available."
    )(select_device)
    mcp.tool(
        description="Get model, Android version, API level, screen size, and health checks."
    )(get_device_info)
