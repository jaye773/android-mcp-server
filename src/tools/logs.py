"""Log monitoring tools for MCP server."""

import logging
from typing import Any, Dict

from ..tool_models import LogcatParams, LogMonitorParams, StopMonitorParams

logger = logging.getLogger(__name__)

# Module-level components storage
_components = {}


async def get_logcat(params: LogcatParams) -> Dict[str, Any]:
    """Get device logs with filtering.

    When to use:
    - Snapshot logs around a specific step or error.

    Tip:
    - Use `priority` (I/W/E) and `tag_filter` to reduce noise.
    """
    try:
        log_monitor = _components.get("log_monitor")
        if not log_monitor:
            return {
                "success": False,
                "error": "Log monitor not initialized",
            }

        return await log_monitor.get_logcat(
            tag_filter=params.tag_filter,
            priority=params.priority,
            max_lines=params.max_lines,
            clear_first=params.clear_first,
        )

    except Exception as e:
        logger.error(f"Get logcat failed: {e}")
        return {"success": False, "error": str(e)}


async def start_log_monitoring(params: LogMonitorParams) -> Dict[str, Any]:
    """Start continuous log monitoring.

    When to use:
    - Observe logs during longer flows or recordings.

    Common combos:
    - `start_log_monitoring` → run actions/recording → `stop_log_monitoring`.
    """
    try:
        log_monitor = _components.get("log_monitor")
        if not log_monitor:
            return {
                "success": False,
                "error": "Log monitor not initialized",
            }

        return await log_monitor.start_log_monitoring(
            tag_filter=params.tag_filter,
            priority=params.priority,
            output_file=params.output_file,
        )

    except Exception as e:
        logger.error(f"Start log monitoring failed: {e}")
        return {"success": False, "error": str(e)}


async def stop_log_monitoring(params: StopMonitorParams) -> Dict[str, Any]:
    """Stop log monitoring session.

    When to use:
    - Finish a monitoring run started by `start_log_monitoring`.
    """
    try:
        log_monitor = _components.get("log_monitor")
        if not log_monitor:
            return {
                "success": False,
                "error": "Log monitor not initialized",
            }

        return await log_monitor.stop_log_monitoring(monitor_id=params.monitor_id)

    except Exception as e:
        logger.error(f"Stop log monitoring failed: {e}")
        return {"success": False, "error": str(e)}


async def list_active_monitors() -> Dict[str, Any]:
    """List active log monitoring sessions.

    When to use:
    - Inspect ongoing monitoring sessions; find IDs for `stop_log_monitoring`.
    """
    try:
        log_monitor = _components.get("log_monitor")
        if not log_monitor:
            return {
                "success": False,
                "error": "Log monitor not initialized",
            }

        return await log_monitor.list_active_monitors()

    except Exception as e:
        logger.error(f"List monitors failed: {e}")
        return {"success": False, "error": str(e)}


def register_log_tools(mcp, components):
    """Register log monitoring tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        components: Dictionary containing initialized components
    """
    global _components
    _components = components

    mcp.tool(
        description=(
            "Fetch recent logcat with tag/priority filters. Critical for LLMs: "
            "limit output size to protect context window. Always set max_lines "
            "(e.g., 50–200) and consider tag_filter plus priority (I/W/E) to reduce noise. "
            "Use clear_first only when you need a clean snapshot of new events."
        )
    )(get_logcat)

    mcp.tool(
        description="Start continuous logcat monitoring; optional file output in ./logs."
    )(start_log_monitoring)

    mcp.tool(description="Stop a specific or all active log monitors; returns stats.")(
        stop_log_monitoring
    )

    mcp.tool(
        description="List active log monitors (IDs, duration, filter, entries processed)."
    )(list_active_monitors)
