"""Media capture tools for MCP server."""

import logging
from typing import Any, Dict

from ..decorators import timeout_wrapper
from ..tool_models import RecordingParams, ScreenshotParams, StopRecordingParams

logger = logging.getLogger(__name__)

# Module-level components storage
_components = {}


@timeout_wrapper()
async def take_screenshot(params: ScreenshotParams) -> Dict[str, Any]:
    """Capture device screenshot.

    When to use:
    - Before/after an action to verify UI changes or for reporting.

    Common combos:
    - `take_screenshot` → action (tap/swipe/input) → `take_screenshot` again.
    """
    try:
        media_capture = _components.get("media_capture")
        if not media_capture:
            return {
                "success": False,
                "error": "Media capture not initialized",
            }

        return await media_capture.take_screenshot(
            filename=params.filename, pull_to_local=params.pull_to_local
        )

    except Exception as e:
        logger.error(f"Take screenshot failed: {e}")
        return {"success": False, "error": str(e)}


async def start_screen_recording(params: RecordingParams) -> Dict[str, Any]:
    """Start screen recording.

    When to use:
    - Capture longer flows, debugging sessions, or test runs.

    Tips:
    - Reduce `bit_rate` or `size_limit` on slow devices.
    - Pair with `start_log_monitoring` to correlate UI + logs.
    """
    try:
        video_recorder = _components.get("video_recorder")
        if not video_recorder:
            return {
                "success": False,
                "error": "Video recorder not initialized",
            }

        return await video_recorder.start_recording(
            filename=params.filename,
            time_limit=params.time_limit,
            bit_rate=params.bit_rate,
            size_limit=params.size_limit,
        )

    except Exception as e:
        logger.error(f"Start recording failed: {e}")
        return {"success": False, "error": str(e)}


async def stop_screen_recording(params: StopRecordingParams) -> Dict[str, Any]:
    """Stop screen recording.

    When to use:
    - End a recording started by `start_screen_recording`.

    Tip:
    - Omit `recording_id` to stop all active sessions.
    """
    try:
        video_recorder = _components.get("video_recorder")
        if not video_recorder:
            return {
                "success": False,
                "error": "Video recorder not initialized",
            }

        return await video_recorder.stop_recording(
            recording_id=params.recording_id, pull_to_local=params.pull_to_local
        )

    except Exception as e:
        logger.error(f"Stop recording failed: {e}")
        return {"success": False, "error": str(e)}


async def list_active_recordings() -> Dict[str, Any]:
    """List active recording sessions.

    When to use:
    - Inspect ongoing captures; find IDs for `stop_screen_recording`.
    """
    try:
        video_recorder = _components.get("video_recorder")
        if not video_recorder:
            return {
                "success": False,
                "error": "Video recorder not initialized",
            }

        return await video_recorder.list_active_recordings()

    except Exception as e:
        logger.error(f"List recordings failed: {e}")
        return {"success": False, "error": str(e)}


def register_media_tools(mcp, components):
    """Register media capture tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        components: Dictionary containing initialized components
    """
    global _components
    _components = components

    mcp.tool(
        description="Capture a screenshot to /sdcard and optionally pull to ./assets."
    )(take_screenshot)

    mcp.tool(
        description="Start screen recording (mp4) with optional bitrate/size/time limits."
    )(start_screen_recording)

    mcp.tool(
        description="Stop a specific or all active recordings and optionally pull files locally."
    )(stop_screen_recording)

    mcp.tool(
        description="List active screen recordings (IDs, duration, device path)."
    )(list_active_recordings)
