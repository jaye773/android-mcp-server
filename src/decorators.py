"""Decorators for MCP tools."""

import asyncio
import logging
from typing import Optional

from .config import DEFAULT_TOOL_TIMEOUT, TOOL_TIMEOUTS
from .timeout import remaining_time, start_deadline

logger = logging.getLogger(__name__)


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
