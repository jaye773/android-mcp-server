"""UI inspection and element finding tools for MCP server."""

import asyncio
import logging
from typing import Any, Dict, Optional

from ..decorators import timeout_wrapper
from ..timeout import remaining_time
from ..tool_models import ElementSearchParams, UILayoutParams
from ..ui_inspector import ElementFinder
from ..validation import create_validation_error_response, log_validation_attempt

logger = logging.getLogger(__name__)

# Module-level components reference
_components = {}


def _transform_element_to_screen_format(
    element: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
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
            "identifier": element.get(
                "resource-id", ""
            ),  # resource-id becomes identifier
            "coordinates": coordinates,
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

        return {"x": x1, "y": y1, "width": width, "height": height}

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
        element.get("text", "").strip()
        or element.get("label", "").strip()
        or element.get("identifier", "").strip()
    )

    is_interactive = bool(
        element.get("clickable")
        or element.get("focusable")
        or element.get("scrollable")
    )

    return has_content or is_interactive


@timeout_wrapper()
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
        ui_inspector = _components.get("ui_inspector")
        if not ui_inspector:
            return {
                "success": False,
                "error": "UI inspector not initialized",
            }

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
        ui_inspector = _components.get("ui_inspector")
        adb_manager = _components.get("adb_manager")

        if not ui_inspector or not adb_manager:
            return {
                "success": False,
                "error": "Components not initialized",
                "elements": [],
            }

        # Fast-fail if no device is connected/selected to avoid long adb retries
        if not adb_manager.selected_device:
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
                            "coordinates": {
                                "x": 0,
                                "y": 0,
                                "width": w,
                                "height": toolbar_h,
                            },
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
                "elements": [],
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
            "total_elements_scanned": len(all_elements),
        }

    except Exception as e:
        logger.error(f"List screen elements failed: {e}")
        return {"success": False, "error": str(e), "elements": []}


@timeout_wrapper()
async def find_elements(params: ElementSearchParams) -> Dict[str, Any]:
    """Find UI elements by various attributes."""
    start_time = asyncio.get_event_loop().time()

    try:
        ui_inspector = _components.get("ui_inspector")
        validator = _components.get("validator")

        if not ui_inspector or not validator:
            return {
                "success": False,
                "error": "Components not initialized",
            }

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
                "timeout_note": "Search operation timed out, returning empty result to avoid delay",
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
            logger.info(
                f"Empty element search took {execution_time:.2f}s - consider UI optimization"
            )
        elif len(elements) == 0:
            logger.debug(
                f"Empty element search completed quickly in {execution_time:.2f}s"
            )

        return {
            "success": True,
            "elements": converted_elements,
            "count": len(elements),
            "search_criteria": sanitized_params,
            "validation_warnings": validation_result.warnings,
            "execution_time": round(execution_time, 2),
        }

    except Exception as e:
        execution_time = asyncio.get_event_loop().time() - start_time
        logger.error(f"Find elements failed after {execution_time:.2f}s: {e}")
        return {
            "success": False,
            "error": str(e),
            "execution_time": round(execution_time, 2),
        }


def register_ui_tools(mcp, components):  # noqa: C901
    """Register UI inspection tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        components: Dictionary containing initialized components
    """
    global _components
    _components = components

    mcp.tool(
        description=(
            "Extract the current UI hierarchy (uiautomator dump). Note: For WebView-heavy "
            "apps like Chrome, prefer `take_screenshot` + coordinate interactions, as dumps "
            "may be slow/limited."
        )
    )(get_ui_layout)

    mcp.tool(
        description=(
            "List visible, meaningful UI elements in an LLM-friendly format "
            "(type/text/label/id/bounds). For heavy WebView apps like Chrome, "
            "prefer `take_screenshot` and interact via coordinates."
        )
    )(list_screen_elements)

    mcp.tool(
        description=(
            "LLM-friendly element lookup. Provide one or more of text, resource_id, "
            "content_desc, or class_name to search the current UI dump. Defaults favor "
            "recall (partial match, enabled_only=True). Use exact_match for strict matching "
            "and index to disambiguate multiple results. Best practice: call find_elements "
            "first to inspect candidates, then call tap_element with the same selector + index."
        )
    )(find_elements)
