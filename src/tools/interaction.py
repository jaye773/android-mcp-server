"""Screen interaction tools for MCP server."""

import logging
from typing import Any, Dict

from ..decorators import timeout_wrapper
from ..tool_models import (
    KeyPressParams,
    SwipeDirectionParams,
    SwipeParams,
    TapCoordinatesParams,
    TapElementParams,
    TextInputParams,
)

logger = logging.getLogger(__name__)

# Module-level components storage
_components = {}


@timeout_wrapper()
async def tap_screen(params: TapCoordinatesParams) -> Dict[str, Any]:
    """Tap screen at specific coordinates.

    When to use:
    - You already know the coordinates (from `get_ui_layout`/`list_screen_elements`).

    Tip:
    - Pair with element bounds to compute the center before tapping.
    """
    try:
        screen_interactor = _components.get("screen_interactor")
        if not screen_interactor:
            return {
                "success": False,
                "error": "Screen interactor not initialized",
            }

        return await screen_interactor.tap_coordinates(params.x, params.y)

    except Exception as e:
        logger.error(f"Tap screen failed: {e}")
        return {"success": False, "error": str(e)}


@timeout_wrapper()
async def tap_element(params: TapElementParams) -> Dict[str, Any]:
    """Find and tap UI element with flexible matching."""
    try:
        screen_interactor = _components.get("screen_interactor")
        if not screen_interactor:
            return {
                "success": False,
                "error": "Screen interactor not initialized",
            }

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


async def swipe_screen(params: SwipeParams) -> Dict[str, Any]:
    """Perform swipe gesture between coordinates.

    When to use:
    - Need precise control over start/end points (e.g., within a specific element).

    Common combo:
    - `get_ui_layout` → compute element bounds → `swipe_screen` inside the element.
    """
    try:
        gesture_controller = _components.get("gesture_controller")
        if not gesture_controller:
            return {
                "success": False,
                "error": "Gesture controller not initialized",
            }

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


async def swipe_direction(params: SwipeDirectionParams) -> Dict[str, Any]:
    """Swipe in a direction (up/down/left/right).

    When to use:
    - Generic scrolling/navigation without targeting a specific element.

    Tips:
    - Omit `distance` to default to ~1/3 of the screen.
    - After swipe, call `get_ui_layout` or `list_screen_elements` to refresh state.
    """
    try:
        gesture_controller = _components.get("gesture_controller")
        if not gesture_controller:
            return {
                "success": False,
                "error": "Gesture controller not initialized",
            }

        return await gesture_controller.swipe_direction(
            direction=params.direction,
            distance=params.distance,
            duration_ms=params.duration_ms,
        )

    except Exception as e:
        logger.error(f"Swipe direction failed: {e}")
        return {"success": False, "error": str(e)}


async def input_text(params: TextInputParams) -> Dict[str, Any]:
    """Input text into the focused field.

    When to use:
    - After focusing an input (e.g., via `tap_screen` on a text field).

    Tip:
    - Set `clear_existing=True` to select-all + delete before typing.
    """
    try:
        text_controller = _components.get("text_controller")
        if not text_controller:
            return {
                "success": False,
                "error": "Text controller not initialized",
            }

        return await text_controller.input_text(
            text=params.text, clear_existing=params.clear_existing, submit=params.submit
        )

    except Exception as e:
        logger.error(f"Input text failed: {e}")
        return {"success": False, "error": str(e)}


async def press_key(params: KeyPressParams) -> Dict[str, Any]:
    """Press device key (BACK, HOME, ENTER, etc.).

    When to use:
    - Navigate back/home, submit forms, dismiss dialogs, etc.

    Tip:
    - Accepts common names (e.g., "back") or explicit `KEYCODE_*` values.
    """
    try:
        text_controller = _components.get("text_controller")
        if not text_controller:
            return {
                "success": False,
                "error": "Text controller not initialized",
            }

        return await text_controller.press_key(params.keycode)

    except Exception as e:
        logger.error(f"Press key failed: {e}")
        return {"success": False, "error": str(e)}


def register_interaction_tools(mcp, components):
    """Register screen interaction tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        components: Dictionary containing initialized components
    """
    global _components
    _components = components

    mcp.tool(description="Tap the screen at specific coordinates (pixels).")(tap_screen)

    mcp.tool(
        description=(
            "Tap a UI element by selector. Intended for agents (Claude/Codex/Gemini) "
            "after a prior find_elements call. Accepts text/resource_id/content_desc "
            "and optional index to disambiguate. By default, clickable_only/enabled_only "
            "are False to improve recall; set them True when you need actionable controls. "
            "Prefer exact_match for deterministic taps."
        )
    )(tap_element)

    mcp.tool(description="Swipe between two coordinates with a duration (ms).")(swipe_screen)

    mcp.tool(
        description="Swipe in a direction (up/down/left/right) from center; distance optional."
    )(swipe_direction)

    mcp.tool(
        description="Type text into the currently focused input field. Optional clear."
    )(input_text)

    mcp.tool(description="Press a device key (e.g., BACK, HOME, ENTER, KEYCODE_*).")(press_key)
