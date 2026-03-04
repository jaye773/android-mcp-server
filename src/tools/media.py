"""Media capture tools for MCP server."""

import logging
from typing import Any, Dict

from ..decorators import timeout_wrapper
from ..registry import ComponentRegistry
from ..tool_models import RecordingParams, ScreenshotParams, StopRecordingParams
from ..validation import (
    FilePathValidator,
    IdentifierValidator,
    create_validation_error_response,
    log_validation_attempt,
)

logger = logging.getLogger(__name__)


@timeout_wrapper()
async def take_screenshot(params: ScreenshotParams) -> Dict[str, Any]:
    """Capture device screenshot.

    When to use:
    - Before/after an action to verify UI changes or for reporting.

    Common combos:
    - `take_screenshot` → action (tap/swipe/input) → `take_screenshot` again.
    """
    try:
        media_capture = ComponentRegistry.instance().get("media_capture")
        if not media_capture:
            return {
                "success": False,
                "error": "Media capture not initialized",
            }

        # Security validation: path traversal detection (must stay)
        if params.filename:
            file_result = FilePathValidator.validate_filename(params.filename)
            if not file_result.is_valid:
                log_validation_attempt("take_screenshot", {"filename": params.filename}, file_result, logger)
                return create_validation_error_response(file_result, "take_screenshot")

        return await media_capture.take_screenshot(
            filename=params.filename, pull_to_local=params.pull_to_local
        )

    except Exception as e:
        logger.error(f"Take screenshot failed: {e}")
        return {"success": False, "error": str(e)}


@timeout_wrapper()
async def start_screen_recording(params: RecordingParams) -> Dict[str, Any]:
    """Start screen recording.

    When to use:
    - Capture longer flows, debugging sessions, or test runs.

    Tips:
    - Reduce `bit_rate` or `size_limit` on slow devices.
    - Pair with `start_log_monitoring` to correlate UI + logs.
    """
    try:
        video_recorder = ComponentRegistry.instance().get("video_recorder")
        if not video_recorder:
            return {
                "success": False,
                "error": "Video recorder not initialized",
            }

        # Security validation: path traversal detection (must stay)
        if params.filename:
            file_result = FilePathValidator.validate_filename(params.filename)
            if not file_result.is_valid:
                log_validation_attempt("start_screen_recording", {"filename": params.filename}, file_result, logger)
                return create_validation_error_response(file_result, "start_screen_recording")

        # time_limit, bit_rate, size_limit validation now handled by Pydantic constraints

        return await video_recorder.start_recording(
            filename=params.filename,
            time_limit=params.time_limit,
            bit_rate=params.bit_rate,
            size_limit=params.size_limit,
        )

    except Exception as e:
        logger.error(f"Start recording failed: {e}")
        return {"success": False, "error": str(e)}


@timeout_wrapper()
async def stop_screen_recording(params: StopRecordingParams) -> Dict[str, Any]:
    """Stop screen recording.

    When to use:
    - End a recording started by `start_screen_recording`.

    Tip:
    - Omit `recording_id` to stop all active sessions.
    """
    try:
        video_recorder = ComponentRegistry.instance().get("video_recorder")
        if not video_recorder:
            return {
                "success": False,
                "error": "Video recorder not initialized",
            }

        # Security validation: shell metacharacter detection (must stay)
        if params.recording_id:
            id_result = IdentifierValidator.validate_identifier(params.recording_id, "recording_id")
            if not id_result.is_valid:
                log_validation_attempt(
                    "stop_screen_recording",
                    {"recording_id": params.recording_id},
                    id_result, logger,
                )
                return create_validation_error_response(id_result, "stop_screen_recording")

        return await video_recorder.stop_recording(
            recording_id=params.recording_id, pull_to_local=params.pull_to_local
        )

    except Exception as e:
        logger.error(f"Stop recording failed: {e}")
        return {"success": False, "error": str(e)}


@timeout_wrapper()
async def list_active_recordings() -> Dict[str, Any]:
    """List active recording sessions.

    When to use:
    - Inspect ongoing captures; find IDs for `stop_screen_recording`.
    """
    try:
        video_recorder = ComponentRegistry.instance().get("video_recorder")
        if not video_recorder:
            return {
                "success": False,
                "error": "Video recorder not initialized",
            }

        return await video_recorder.list_active_recordings()

    except Exception as e:
        logger.error(f"List recordings failed: {e}")
        return {"success": False, "error": str(e)}


def register_media_tools(mcp):
    """Register media capture tools with the MCP server.

    Args:
        mcp: FastMCP server instance
    """
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
