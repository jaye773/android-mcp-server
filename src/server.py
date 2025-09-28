"""Main MCP server implementation for Android device automation."""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union, Callable, Awaitable, Tuple

from mcp.server.fastmcp import FastMCP
from mcp.types import JSONRPCError
from pydantic import BaseModel, Field, ConfigDict

from .adb_manager import ADBManager
from .ui_inspector import UILayoutExtractor, ElementFinder
from .screen_interactor import ScreenInteractor, GestureController, TextInputController
from .media_capture import MediaCapture, VideoRecorder
from .log_monitor import LogMonitor
from .validation import (
    ComprehensiveValidator,
    SecurityLevel,
    ValidationResult,
    create_validation_error_response,
    log_validation_attempt,
)
from .error_handler import (
    ErrorHandler,
    AndroidMCPError,
    ErrorCode,
    get_recovery_suggestions,
)

# Configure logging to stderr (not stdout for STDIO transport)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("android-mcp-server")

# Global components
adb_manager: Optional[ADBManager] = None
ui_inspector: Optional[UILayoutExtractor] = None
screen_interactor: Optional[ScreenInteractor] = None
gesture_controller: Optional[GestureController] = None
text_controller: Optional[TextInputController] = None
media_capture: Optional[MediaCapture] = None
video_recorder: Optional[VideoRecorder] = None
log_monitor: Optional[LogMonitor] = None

# Initialize validator with strict security by default
validator: ComprehensiveValidator = ComprehensiveValidator(SecurityLevel.STRICT)

# Timeout configuration for MCP tools (in seconds) - RE-ENABLED
TOOL_TIMEOUTS = {
    # Device management tools
    "get_devices": 15,
    "select_device": 10,
    "get_device_info": 20,

    # UI tools
    "get_ui_layout": 10,
    "list_screen_elements": 10,  # Added missing entry
    "find_elements": 8,

    # Interaction tools
    "tap_screen": 5,
    "tap_element": 10,
    "swipe_screen": 15,
    "swipe_direction": 15,
    "input_text": 20,
    "press_key": 10,

    # Media tools
    "take_screenshot": 8,
    "start_screen_recording": 15,
    "stop_screen_recording": 20,
    "list_active_recordings": 5,

    # Log tools
    "get_logcat": 10,
    "start_log_monitoring": 10,
    "stop_log_monitoring": 15,
    "list_active_monitors": 5,
}

DEFAULT_TOOL_TIMEOUT = 30  # Default timeout for tools not in the list


from .timeout import start_deadline, remaining_time


# Deadline-based timeout wrapper using asyncio.timeout (Py 3.11+)
def timeout_wrapper(timeout_seconds: Optional[int] = None):
    """Decorator to enforce per-tool deadline and expose remaining budget.

    - Starts a deadline context for the tool execution so inner operations can
      call remaining_time() for budgeting.
    - Enforces the total limit using asyncio.timeout.
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            tool_name = func.__name__
            total_budget = float(
                timeout_seconds or TOOL_TIMEOUTS.get(tool_name, DEFAULT_TOOL_TIMEOUT)
            )
            try:
                async with start_deadline(total_budget):
                    async with asyncio.timeout(total_budget):
                        return await func(*args, **kwargs)
            except (asyncio.TimeoutError, TimeoutError):
                elapsed = round(total_budget - max(0.0, remaining_time(default=0.0)), 2)
                logger.warning(
                    f"Tool {tool_name} timed out after ~{elapsed}/{total_budget}s"
                )
                return {
                    "success": False,
                    "error": f"Operation timed out after {total_budget} seconds",
                    "error_code": "OPERATION_TIMEOUT",
                    "timeout_seconds": total_budget,
                    "elapsed_seconds": elapsed,
                    "tool_name": tool_name,
                    "recovery_suggestions": [
                        "Check device connection and responsiveness",
                        "Try the operation again with a shorter scope",
                        "Restart the device if it appears frozen",
                        "Check for device performance issues",
                    ],
                }
            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")
                return {
                    "success": False,
                    "error": f"Tool execution failed: {str(e)}",
                    "error_code": "TOOL_EXECUTION_ERROR",
                    "tool_name": tool_name,
                }

        return wrapper

    return decorator



# Pydantic models for tool parameters
class DeviceSelectionParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"device_id": "emulator-5554"},
                {"device_id": "DA1A2BC3DEF4"},
                {"device_id": None},
            ]
        }
    )
    device_id: Optional[str] = Field(
        default=None, description="Specific device ID to select"
    )


class UILayoutParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"compressed": True, "include_invisible": False},
                {"compressed": False, "include_invisible": True},
            ]
        }
    )
    compressed: bool = Field(default=True, description="Use compressed UI dump")
    include_invisible: bool = Field(
        default=False, description="Include invisible elements"
    )


class ElementSearchParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"text": "Settings", "clickable_only": True},
                {
                    "resource_id": "com.app:id/login_button",
                    "enabled_only": True,
                    "exact_match": True,
                },
                {"content_desc": "Submit", "class_name": "android.widget.Button"},
            ]
        }
    )
    text: Optional[str] = Field(default=None, description="Text content to search for")
    resource_id: Optional[str] = Field(default=None, description="Resource ID to match")
    content_desc: Optional[str] = Field(
        default=None, description="Content description to match"
    )
    class_name: Optional[str] = Field(default=None, description="Class name to match")
    clickable_only: bool = Field(
        default=False, description="Only return clickable elements"
    )
    enabled_only: bool = Field(default=True, description="Only return enabled elements")
    exact_match: bool = Field(default=False, description="Use exact string matching")


class TapCoordinatesParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"x": 540, "y": 1600},
                {"x": 100, "y": 300},
            ]
        }
    )
    x: int = Field(description="X coordinate")
    y: int = Field(description="Y coordinate")


class TapElementParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"text": "Login", "index": 0},
                {"resource_id": "com.app:id/submit", "index": 0},
                {"content_desc": "Navigate up", "index": 0},
            ]
        }
    )
    text: Optional[str] = Field(default=None, description="Text to find and tap")
    resource_id: Optional[str] = Field(
        default=None, description="Resource ID to find and tap"
    )
    content_desc: Optional[str] = Field(
        default=None, description="Content description to find and tap"
    )
    index: int = Field(default=0, description="Index of element if multiple matches")
    clickable_only: bool = Field(
        default=False, description="Only find clickable elements (default: False for flexibility)"
    )
    enabled_only: bool = Field(
        default=False, description="Only find enabled elements (default: False for flexibility)"
    )


class SwipeParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"start_x": 540, "start_y": 1600, "end_x": 540, "end_y": 600, "duration_ms": 400},
                {"start_x": 100, "start_y": 400, "end_x": 900, "end_y": 400},
            ]
        }
    )
    start_x: int = Field(description="Start X coordinate")
    start_y: int = Field(description="Start Y coordinate")
    end_x: int = Field(description="End X coordinate")
    end_y: int = Field(description="End Y coordinate")
    duration_ms: int = Field(default=300, description="Swipe duration in milliseconds")


class SwipeDirectionParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"direction": "up", "distance": 600, "duration_ms": 500},
                {"direction": "left"},
            ]
        }
    )
    direction: str = Field(description="Swipe direction: up, down, left, right")
    distance: Optional[int] = Field(
        default=None, description="Swipe distance in pixels"
    )
    duration_ms: int = Field(default=300, description="Swipe duration in milliseconds")


class TextInputParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"text": "hello world", "clear_existing": False},
                {"text": "user@example.com", "clear_existing": True},
            ]
        }
    )
    text: str = Field(description="Text to input")
    clear_existing: bool = Field(default=False, description="Clear existing text first")
    submit: bool = Field(default=False, description="Whether to submit the text by pressing Enter")


class KeyPressParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"keycode": "BACK"},
                {"keycode": "ENTER"},
                {"keycode": "KEYCODE_VOLUME_UP"},
            ]
        }
    )
    keycode: str = Field(description="Key code or name (BACK, HOME, ENTER, etc.)")


class ScreenshotParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"filename": "before_action.png", "pull_to_local": True},
                {"pull_to_local": True},
            ]
        }
    )
    filename: Optional[str] = Field(default=None, description="Custom filename")
    pull_to_local: bool = Field(default=True, description="Download to local machine")


class RecordingParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"filename": "flow.mp4", "time_limit": 120, "bit_rate": "4M", "size_limit": "720x1280"},
                {"time_limit": 60},
            ]
        }
    )
    filename: Optional[str] = Field(default=None, description="Custom filename")
    time_limit: int = Field(default=180, description="Recording time limit in seconds")
    bit_rate: Optional[str] = Field(
        default=None, description="Video bit rate (e.g., '4M')"
    )
    size_limit: Optional[str] = Field(
        default=None, description="Resolution limit (e.g., '720x1280')"
    )


class StopRecordingParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"recording_id": "emulator-5554_recording_20250101_101500.mp4", "pull_to_local": True},
                {"pull_to_local": True},
            ]
        }
    )
    recording_id: Optional[str] = Field(
        default=None, description="Specific recording to stop"
    )
    pull_to_local: bool = Field(default=True, description="Download to local machine")


class LogcatParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"tag_filter": "ActivityManager", "priority": "I", "max_lines": 200},
                {"priority": "E", "max_lines": 100, "clear_first": True},
            ]
        }
    )
    tag_filter: Optional[str] = Field(default=None, description="Filter by tag")
    priority: str = Field(
        default="V", description="Minimum log priority (V/D/I/W/E/F/S)"
    )
    max_lines: int = Field(default=100, description="Maximum lines to return")
    clear_first: bool = Field(default=False, description="Clear logcat buffer first")


class LogMonitorParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"tag_filter": "MyApp", "priority": "D", "output_file": "myapp.log"},
                {"priority": "I"},
            ]
        }
    )
    tag_filter: Optional[str] = Field(default=None, description="Filter by tag")
    priority: str = Field(default="I", description="Minimum log priority")
    output_file: Optional[str] = Field(default=None, description="Save to file")


class StopMonitorParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"monitor_id": "logmon_emulator-5554_20250101_101500"},
                {"monitor_id": None},
            ]
        }
    )
    monitor_id: Optional[str] = Field(
        default=None, description="Specific monitor to stop"
    )


async def initialize_components() -> None:
    """Initialize all server components."""
    global adb_manager, ui_inspector, screen_interactor, gesture_controller
    global text_controller, media_capture, video_recorder, log_monitor

    try:
        # Initialize ADB manager
        adb_manager = ADBManager()

        # Auto-select first device
        device_result = await adb_manager.auto_select_device()
        if device_result["success"]:
            logger.info(f"Auto-selected device: {device_result['selected']['id']}")
        else:
            logger.warning(f"No devices available: {device_result.get('error')}")

        # Initialize other components
        ui_inspector = UILayoutExtractor(adb_manager)
        screen_interactor = ScreenInteractor(adb_manager, ui_inspector)
        gesture_controller = GestureController(adb_manager)
        text_controller = TextInputController(adb_manager)
        media_capture = MediaCapture(adb_manager)
        video_recorder = VideoRecorder(adb_manager)
        log_monitor = LogMonitor(adb_manager)

        logger.info("All components initialized successfully")

    except Exception as e:
        logger.error(f"Component initialization failed: {e}")
        raise


# Device Management Tools
@timeout_wrapper()
@mcp.tool(description="List connected Android devices and basic status via ADB.")
async def get_devices() -> Dict[str, Any]:
    """List connected Android devices.

    When to use:
    - First step to discover devices before selecting one.
    - If other tools report "No device selected" or device issues.

    Common combos:
    - `get_devices` → `select_device` → `get_device_info`.
    """
    try:
        if not adb_manager:
            await initialize_components()

        devices = await adb_manager.list_devices()
        return {"success": True, "devices": devices, "count": len(devices)}
    except Exception as e:
        logger.error(f"Get devices failed: {e}")
        return {"success": False, "error": str(e)}


@timeout_wrapper()
@mcp.tool(description="Select a specific device by ID or auto-select the first available.")
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
        if not adb_manager:
            await initialize_components()

        if params.device_id:
            # Validate device ID
            from .validation import DeviceIdValidator

            validation_result = DeviceIdValidator.validate_device_id(params.device_id)

            if not validation_result.is_valid:
                log_validation_attempt(
                    "select_device",
                    {"device_id": params.device_id},
                    validation_result,
                    logger,
                )
                return create_validation_error_response(
                    validation_result, "device selection"
                )

            # Log validation warnings if any
            if validation_result.warnings:
                log_validation_attempt(
                    "select_device",
                    {"device_id": params.device_id},
                    validation_result,
                    logger,
                )

            # Select specific device
            adb_manager.selected_device = validation_result.sanitized_value
            health = await adb_manager.check_device_health(
                validation_result.sanitized_value
            )

            return {
                "success": True,
                "selected_device": validation_result.sanitized_value,
                "health": health,
                "validation_warnings": validation_result.warnings,
            }
        else:
            # Auto-select first device
            result = await adb_manager.auto_select_device()
            return result

    except Exception as e:
        logger.error(f"Select device failed: {e}")
        return {"success": False, "error": str(e)}


@timeout_wrapper()
@mcp.tool(description="Get model, Android version, API level, screen size, and health checks.")
async def get_device_info() -> Dict[str, Any]:
    """Get detailed information about the selected device.

    When to use:
    - Validate connection and capabilities before automation.
    - Size-aware gestures (e.g., directional swipes) depend on screen size.

    Common combos:
    - `select_device` → `get_device_info` → `swipe_direction` or UI actions.
    """
    try:
        if not adb_manager:
            await initialize_components()

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


# UI Layout and Inspection Tools
@timeout_wrapper()
@mcp.tool(description="Extract the current UI hierarchy (uiautomator dump). Note: For WebView-heavy apps like Chrome, prefer `take_screenshot` + coordinate interactions, as dumps may be slow/limited.")
async def get_ui_layout(params: UILayoutParams) -> Dict[str, Any]:
    """Extract the current UI hierarchy.

    When to use:
    - Before searching or tapping elements; to understand screen structure.

    Tips:
    - Set `compressed=False` for a fuller tree if element matches are missing.
    - `include_invisible=True` to diagnose hidden/offscreen elements.
    - WebView-heavy screens (e.g., Chrome) may yield slow/partial dumps. Prefer
      `take_screenshot` and operate via `tap_screen`/`swipe_direction` using coordinates
      when dumps are unreliable.

    Common combos:
    - `get_ui_layout` → client-side filtering → `tap_screen`/`swipe_direction`.
    - `get_ui_layout` → `list_screen_elements` for LLM-friendly view.
    """
    try:
        if not ui_inspector:
            await initialize_components()

        result = await ui_inspector.get_ui_layout(
            compressed=params.compressed, include_invisible=params.include_invisible
        )

        # Convert elements to dict format for JSON serialization
        if result["success"] and "elements" in result:
            finder = ElementFinder(ui_inspector)
            converted_elements = []
            for element in result["elements"]:
                if isinstance(element, dict):
                    # Element is already a dict, use it as-is
                    converted_elements.append(element)
                else:
                    # Element is a UIElement object, convert to dict
                    converted_elements.append(finder.element_to_dict(element))
            result["elements"] = converted_elements

        return result

    except Exception as e:
        logger.error(f"Get UI layout failed: {e}")
        return {"success": False, "error": str(e)}


@timeout_wrapper()
@mcp.tool(description="List visible, meaningful UI elements in an LLM-friendly format (type/text/label/id/bounds). For heavy WebView apps like Chrome, prefer `take_screenshot` and interact via coordinates.")
async def list_screen_elements() -> Dict[str, Any]:
    """List all interactive elements currently visible on screen in LLM-friendly format.

    Returns all meaningful elements (with text, labels, or interactive capabilities)
    in the same format as mobile-next/mobile-mcp for optimal LLM consumption.

    When to use:
    - Provide a concise, actionable element list for an agent to choose from.

    Common combos:
    - `list_screen_elements` → choose element → `tap_screen` at its center.

    Important:
    - WebView-heavy screens (e.g., Chrome) may limit/slow UI dumps. In these cases,
      prefer `take_screenshot` for visual grounding and then use `tap_screen`/`swipe_direction`
      with coordinates derived from the screenshot.
    """
    try:
        if not ui_inspector:
            await initialize_components()

        # Fast-fail if no device is connected/selected to avoid long adb retries
        if not adb_manager:
            await initialize_components()

        if adb_manager and not adb_manager.selected_device:
            devices = await adb_manager.list_devices()
            if not devices:
                return {
                    "success": False,
                    "error": "No Android devices connected",
                    "elements": [],
                    "recovery_suggestions": [
                        "Connect a device and enable USB debugging",
                        "Run 'adb devices' to verify detection",
                        "Use select_device if multiple devices are present",
                    ],
                }
            # Try auto-selecting a device once
            auto = await adb_manager.auto_select_device()
            if not auto.get("success"):
                return {
                    "success": False,
                    "error": auto.get("error", "Unable to select a device"),
                    "devices": devices,
                    "elements": [],
                }

        # Detect Chrome foreground and adjust behavior to avoid heavy dumps that may hang
        is_chrome = False
        foreground_info = await adb_manager.get_foreground_app()
        if foreground_info.get("success"):
            pkg = (foreground_info.get("package") or "").lower()
            if any(k in pkg for k in ["chrome", "org.chromium", "com.android.chrome"]):
                is_chrome = True

        # Get all UI elements with tight timeout and no internal retries to avoid hanging
        try:
            quick_timeout = 4.0 if is_chrome else 6.0
            adb_to = 3 if is_chrome else 5
            layout_result = await asyncio.wait_for(
                ui_inspector.get_ui_layout(
                    compressed=True,
                    include_invisible=False,
                    retry_on_failure=False,
                    max_retries=1,
                    adb_timeout=adb_to,
                ),
                timeout=quick_timeout,
            )
        except asyncio.TimeoutError:
            # Graceful Chrome fallback: synthesize minimal elements to keep the agent moving
            if is_chrome:
                size = await adb_manager.get_screen_size()
                if size.get("success"):
                    w = size["width"]
                    h = size["height"]
                    toolbar_h = max(48, int(h * 0.10))  # approx toolbar height
                    elements = [
                        {
                            "type": "android.view.ViewGroup",
                            "text": "",
                            "label": "Chrome toolbar",
                            "identifier": "",
                            "coordinates": {"x": 0, "y": 0, "width": w, "height": toolbar_h},
                            "clickable": True,
                            "enabled": True,
                        },
                        {
                            "type": "android.webkit.WebView",
                            "text": "",
                            "label": "Page content",
                            "identifier": "",
                            "coordinates": {
                                "x": 0,
                                "y": toolbar_h,
                                "width": w,
                                "height": max(1, h - toolbar_h),
                            },
                            "scrollable": True,
                            "enabled": True,
                        },
                    ]
                    return {
                        "success": True,
                        "elements": elements,
                        "count": len(elements),
                        "mode": "fallback_chrome",
                        "note": "Returned synthesized elements to avoid Chrome UI dump hang",
                    }
            return {
                "success": False,
                "error": "Timed out retrieving UI layout",
                "timeout_seconds": quick_timeout,
                "elements": [],
                "recovery_suggestions": [
                    "Ensure device is unlocked and responsive",
                    "Try again or use get_ui_layout directly for more detail",
                ],
            }

        if not layout_result["success"]:
            return {
                "success": False,
                "error": layout_result.get("error", "Failed to extract UI layout"),
                "elements": []
            }

        all_elements = layout_result.get("elements", [])

        # Filter and transform elements to LLM-friendly format
        screen_elements = []
        for element in all_elements:
            transformed_element = _transform_element_to_screen_format(element)
            if transformed_element and _is_meaningful_element(transformed_element):
                screen_elements.append(transformed_element)

        return {
            "success": True,
            "elements": screen_elements,
            "count": len(screen_elements),
            "total_elements_scanned": len(all_elements)
        }

    except Exception as e:
        logger.error(f"List screen elements failed: {e}")
        return {"success": False, "error": str(e), "elements": []}


def _transform_element_to_screen_format(element: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Transform Android MCP element format to mobile-next compatible format."""
    try:
        # Parse bounds from "[x1,y1][x2,y2]" to coordinates
        bounds_str = element.get("bounds", "[0,0][0,0]")
        coordinates = _parse_bounds_to_coordinates(bounds_str)

        if not coordinates:
            return None

        # Transform to mobile-next format
        screen_element = {
            "type": element.get("class", ""),
            "text": element.get("text", ""),
            "label": element.get("content-desc", ""),  # content-desc becomes label
            "identifier": element.get("resource-id", ""),  # resource-id becomes identifier
            "coordinates": coordinates
        }

        # Add optional properties if present
        if element.get("clickable") == "true":
            screen_element["clickable"] = True
        if element.get("enabled") == "true":
            screen_element["enabled"] = True
        if element.get("focusable") == "true":
            screen_element["focusable"] = True
        if element.get("scrollable") == "true":
            screen_element["scrollable"] = True

        return screen_element

    except Exception as e:
        logger.warning(f"Failed to transform element: {e}")
        return None


def _parse_bounds_to_coordinates(bounds_str: str) -> Optional[Dict[str, int]]:
    """Convert bounds string '[x1,y1][x2,y2]' to coordinates {x, y, width, height}."""
    try:
        if not bounds_str or bounds_str.strip() == "":
            return None

        # Remove brackets and split coordinates
        clean = bounds_str.replace("[", "").replace("]", ",")
        coords = [int(x) for x in clean.split(",") if x.strip()]

        if len(coords) != 4:
            return None

        x1, y1, x2, y2 = coords

        # Validate coordinates make sense
        if x1 > x2 or y1 > y2:
            return None

        width = x2 - x1
        height = y2 - y1

        # Reject zero-size elements
        if width <= 0 or height <= 0:
            return None

        return {
            "x": x1,
            "y": y1,
            "width": width,
            "height": height
        }

    except (ValueError, IndexError):
        return None


def _is_meaningful_element(element: Dict[str, Any]) -> bool:
    """Check if element is meaningful for LLM interaction (has content or is interactive)."""
    # Element is meaningful if it has:
    # 1. Text content
    # 2. Accessibility label (content description)
    # 3. Resource identifier
    # 4. Is clickable/focusable/scrollable
    # 5. Has reasonable size (width > 0, height > 0)

    coords = element.get("coordinates", {})
    if coords.get("width", 0) <= 0 or coords.get("height", 0) <= 0:
        return False

    has_content = bool(
        element.get("text", "").strip() or
        element.get("label", "").strip() or
        element.get("identifier", "").strip()
    )

    is_interactive = bool(
        element.get("clickable") or
        element.get("focusable") or
        element.get("scrollable")
    )

    return has_content or is_interactive


@timeout_wrapper()
@mcp.tool(description="LLM-friendly element lookup. Provide one or more of text, resource_id, content_desc, or class_name to search the current UI dump. Defaults favor recall (partial match, enabled_only=True). Use exact_match for strict matching and index to disambiguate multiple results. Best practice: call find_elements first to inspect candidates, then call tap_element with the same selector + index.")
async def find_elements(params: ElementSearchParams) -> Dict[str, Any]:
    """Find UI elements by various attributes."""
    start_time = asyncio.get_event_loop().time()

    try:
        if not ui_inspector:
            await initialize_components()

        # Validate element search parameters
        validation_result = validator.validate_element_search(
            text=params.text,
            resource_id=params.resource_id,
            content_desc=params.content_desc,
            class_name=params.class_name,
        )

        if not validation_result.is_valid:
            log_validation_attempt(
                "find_elements", params.model_dump(), validation_result, logger
            )
            return create_validation_error_response(validation_result, "element search")

        # Log validation warnings if any
        if validation_result.warnings:
            log_validation_attempt(
                "find_elements", params.dict(), validation_result, logger
            )

        # Use sanitized parameters
        sanitized_params = validation_result.sanitized_value
        finder = ElementFinder(ui_inspector)

        try:
            # Budget a portion of the remaining time for the search stage
            inner_timeout = max(0.1, min(6.0, remaining_time()))
            async with asyncio.timeout(inner_timeout):
                elements = await finder.find_elements(
                    text=sanitized_params.get("text"),
                    resource_id=sanitized_params.get("resource_id"),
                    content_desc=sanitized_params.get("content_desc"),
                    class_name=sanitized_params.get("class_name"),
                    clickable_only=params.clickable_only,
                    enabled_only=params.enabled_only,
                    exact_match=params.exact_match,
                )
        except (asyncio.TimeoutError, TimeoutError):
            # If the search times out, return empty result immediately
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.info(
                f"Element search stage timed out (~{inner_timeout:.2f}s budget). "
                f"Returning empty result (total time: {execution_time:.2f}s)"
            )
            return {
                "success": False,
                "elements": [],
                "count": 0,
                "search_criteria": sanitized_params,
                "validation_warnings": validation_result.warnings,
                "timeout_note": "Search operation timed out, returning empty result to avoid delay"
            }

        # Convert elements to dict format for JSON serialization
        converted_elements = []
        for element in elements:
            if isinstance(element, dict):
                # Element is already a dict, use it as-is
                converted_elements.append(element)
            else:
                # Element is a UIElement object, convert to dict
                converted_elements.append(finder.element_to_dict(element))

        execution_time = asyncio.get_event_loop().time() - start_time

        # Log performance for debugging
        if len(elements) == 0 and execution_time > 1.0:
            logger.info(f"Empty element search took {execution_time:.2f}s - consider UI optimization")
        elif len(elements) == 0:
            logger.debug(f"Empty element search completed quickly in {execution_time:.2f}s")

        return {
            "success": True,
            "elements": converted_elements,
            "count": len(elements),
            "search_criteria": sanitized_params,
            "validation_warnings": validation_result.warnings,
            "execution_time": round(execution_time, 2)
        }

    except Exception as e:
        execution_time = asyncio.get_event_loop().time() - start_time
        logger.error(f"Find elements failed after {execution_time:.2f}s: {e}")
        return {"success": False, "error": str(e), "execution_time": round(execution_time, 2)}


# Screen Interaction Tools
@timeout_wrapper()
@mcp.tool(description="Tap the screen at specific coordinates (pixels).")
async def tap_screen(params: TapCoordinatesParams) -> Dict[str, Any]:
    """Tap screen at specific coordinates.

    When to use:
    - You already know the coordinates (from `get_ui_layout`/`list_screen_elements`).

    Tip:
    - Pair with element bounds to compute the center before tapping.
    """
    try:
        if not screen_interactor:
            await initialize_components()

        return await screen_interactor.tap_coordinates(params.x, params.y)

    except Exception as e:
        logger.error(f"Tap screen failed: {e}")
        return {"success": False, "error": str(e)}


@timeout_wrapper()
@mcp.tool(description="Tap a UI element by selector. Intended for agents (Claude/Codex/Gemini) after a prior find_elements call. Accepts text/resource_id/content_desc and optional index to disambiguate. By default, clickable_only/enabled_only are False to improve recall; set them True when you need actionable controls. Prefer exact_match for deterministic taps.")
async def tap_element(params: TapElementParams) -> Dict[str, Any]:
    """Find and tap UI element with flexible matching."""
    try:
        if not screen_interactor:
            await initialize_components()

        return await screen_interactor.tap_element(
            text=params.text,
            resource_id=params.resource_id,
            content_desc=params.content_desc,
            index=params.index,
            clickable_only=params.clickable_only,
            enabled_only=params.enabled_only,
        )

    except Exception as e:
        logger.error(f"Tap element failed: {e}")
        return {"success": False, "error": str(e)}


# @timeout_wrapper()
@mcp.tool(description="Swipe between two coordinates with a duration (ms).")
async def swipe_screen(params: SwipeParams) -> Dict[str, Any]:
    """Perform swipe gesture between coordinates.

    When to use:
    - Need precise control over start/end points (e.g., within a specific element).

    Common combo:
    - `get_ui_layout` → compute element bounds → `swipe_screen` inside the element.
    """
    try:
        if not gesture_controller:
            await initialize_components()

        return await gesture_controller.swipe_coordinates(
            params.start_x,
            params.start_y,
            params.end_x,
            params.end_y,
            params.duration_ms,
        )

    except Exception as e:
        logger.error(f"Swipe screen failed: {e}")
        return {"success": False, "error": str(e)}


# @timeout_wrapper()
@mcp.tool(description="Swipe in a direction (up/down/left/right) from center; distance optional.")
async def swipe_direction(params: SwipeDirectionParams) -> Dict[str, Any]:
    """Swipe in a direction (up/down/left/right).

    When to use:
    - Generic scrolling/navigation without targeting a specific element.

    Tips:
    - Omit `distance` to default to ~1/3 of the screen.
    - After swipe, call `get_ui_layout` or `list_screen_elements` to refresh state.
    """
    try:
        if not gesture_controller:
            await initialize_components()

        return await gesture_controller.swipe_direction(
            direction=params.direction,
            distance=params.distance,
            duration_ms=params.duration_ms,
        )

    except Exception as e:
        logger.error(f"Swipe direction failed: {e}")
        return {"success": False, "error": str(e)}


# @timeout_wrapper()
@mcp.tool(description="Type text into the currently focused input field. Optional clear.")
async def input_text(params: TextInputParams) -> Dict[str, Any]:
    """Input text into the focused field.

    When to use:
    - After focusing an input (e.g., via `tap_screen` on a text field).

    Tip:
    - Set `clear_existing=True` to select-all + delete before typing.
    """
    try:
        if not text_controller:
            await initialize_components()

        return await text_controller.input_text(
            text=params.text, clear_existing=params.clear_existing, submit=params.submit
        )

    except Exception as e:
        logger.error(f"Input text failed: {e}")
        return {"success": False, "error": str(e)}


# @timeout_wrapper()
@mcp.tool(description="Press a device key (e.g., BACK, HOME, ENTER, KEYCODE_*).")
async def press_key(params: KeyPressParams) -> Dict[str, Any]:
    """Press device key (BACK, HOME, ENTER, etc.).

    When to use:
    - Navigate back/home, submit forms, dismiss dialogs, etc.

    Tip:
    - Accepts common names (e.g., "back") or explicit `KEYCODE_*` values.
    """
    try:
        if not text_controller:
            await initialize_components()

        return await text_controller.press_key(params.keycode)

    except Exception as e:
        logger.error(f"Press key failed: {e}")
        return {"success": False, "error": str(e)}


# Media Capture Tools
@timeout_wrapper()
@mcp.tool(description="Capture a screenshot to /sdcard and optionally pull to ./assets.")
async def take_screenshot(params: ScreenshotParams) -> Dict[str, Any]:
    """Capture device screenshot.

    When to use:
    - Before/after an action to verify UI changes or for reporting.

    Common combos:
    - `take_screenshot` → action (tap/swipe/input) → `take_screenshot` again.
    """
    try:
        if not media_capture:
            await initialize_components()

        return await media_capture.take_screenshot(
            filename=params.filename, pull_to_local=params.pull_to_local
        )

    except Exception as e:
        logger.error(f"Take screenshot failed: {e}")
        return {"success": False, "error": str(e)}


# @timeout_wrapper()
@mcp.tool(description="Start screen recording (mp4) with optional bitrate/size/time limits.")
async def start_screen_recording(params: RecordingParams) -> Dict[str, Any]:
    """Start screen recording.

    When to use:
    - Capture longer flows, debugging sessions, or test runs.

    Tips:
    - Reduce `bit_rate` or `size_limit` on slow devices.
    - Pair with `start_log_monitoring` to correlate UI + logs.
    """
    try:
        if not video_recorder:
            await initialize_components()

        return await video_recorder.start_recording(
            filename=params.filename,
            time_limit=params.time_limit,
            bit_rate=params.bit_rate,
            size_limit=params.size_limit,
        )

    except Exception as e:
        logger.error(f"Start recording failed: {e}")
        return {"success": False, "error": str(e)}


# @timeout_wrapper()
@mcp.tool(description="Stop a specific or all active recordings and optionally pull files locally.")
async def stop_screen_recording(params: StopRecordingParams) -> Dict[str, Any]:
    """Stop screen recording.

    When to use:
    - End a recording started by `start_screen_recording`.

    Tip:
    - Omit `recording_id` to stop all active sessions.
    """
    try:
        if not video_recorder:
            await initialize_components()

        return await video_recorder.stop_recording(
            recording_id=params.recording_id, pull_to_local=params.pull_to_local
        )

    except Exception as e:
        logger.error(f"Stop recording failed: {e}")
        return {"success": False, "error": str(e)}


# @timeout_wrapper()
@mcp.tool(description="List active screen recordings (IDs, duration, device path).")
async def list_active_recordings() -> Dict[str, Any]:
    """List active recording sessions.

    When to use:
    - Inspect ongoing captures; find IDs for `stop_screen_recording`.
    """
    try:
        if not video_recorder:
            await initialize_components()

        return await video_recorder.list_active_recordings()

    except Exception as e:
        logger.error(f"List recordings failed: {e}")
        return {"success": False, "error": str(e)}


# Log Monitoring Tools
# @timeout_wrapper()
@mcp.tool(description="Fetch recent logcat with tag/priority filters. Critical for LLMs: limit output size to protect context window. Always set max_lines (e.g., 50–200) and consider tag_filter plus priority (I/W/E) to reduce noise. Use clear_first only when you need a clean snapshot of new events.")
async def get_logcat(params: LogcatParams) -> Dict[str, Any]:
    """Get device logs with filtering.

    When to use:
    - Snapshot logs around a specific step or error.

    Tip:
    - Use `priority` (I/W/E) and `tag_filter` to reduce noise.
    """
    try:
        if not log_monitor:
            await initialize_components()

        return await log_monitor.get_logcat(
            tag_filter=params.tag_filter,
            priority=params.priority,
            max_lines=params.max_lines,
            clear_first=params.clear_first,
        )

    except Exception as e:
        logger.error(f"Get logcat failed: {e}")
        return {"success": False, "error": str(e)}


# @timeout_wrapper()
@mcp.tool(description="Start continuous logcat monitoring; optional file output in ./logs.")
async def start_log_monitoring(params: LogMonitorParams) -> Dict[str, Any]:
    """Start continuous log monitoring.

    When to use:
    - Observe logs during longer flows or recordings.

    Common combos:
    - `start_log_monitoring` → run actions/recording → `stop_log_monitoring`.
    """
    try:
        if not log_monitor:
            await initialize_components()

        return await log_monitor.start_log_monitoring(
            tag_filter=params.tag_filter,
            priority=params.priority,
            output_file=params.output_file,
        )

    except Exception as e:
        logger.error(f"Start log monitoring failed: {e}")
        return {"success": False, "error": str(e)}


# @timeout_wrapper()
@mcp.tool(description="Stop a specific or all active log monitors; returns stats.")
async def stop_log_monitoring(params: StopMonitorParams) -> Dict[str, Any]:
    """Stop log monitoring session.

    When to use:
    - Finish a monitoring run started by `start_log_monitoring`.
    """
    try:
        if not log_monitor:
            await initialize_components()

        return await log_monitor.stop_log_monitoring(monitor_id=params.monitor_id)

    except Exception as e:
        logger.error(f"Stop log monitoring failed: {e}")
        return {"success": False, "error": str(e)}


# @timeout_wrapper()
@mcp.tool(description="List active log monitors (IDs, duration, filter, entries processed).")
async def list_active_monitors() -> Dict[str, Any]:
    """List active log monitoring sessions.

    When to use:
    - Inspect ongoing monitoring sessions; find IDs for `stop_log_monitoring`.
    """
    try:
        if not log_monitor:
            await initialize_components()

        return await log_monitor.list_active_monitors()

    except Exception as e:
        logger.error(f"List monitors failed: {e}")
        return {"success": False, "error": str(e)}


def main() -> None:
    """Run the MCP server."""
    logger.info("Starting Android MCP server...")

    # Initialize components before starting server
    async def init_and_run() -> None:
        await initialize_components()
        await mcp.run_stdio_async()

    asyncio.run(init_and_run())


if __name__ == "__main__":
    main()
