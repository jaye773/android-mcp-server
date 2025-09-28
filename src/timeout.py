"""Deadline-based timeout helpers for MCP tools.

Provides a simple deadline context that tools can start once and
sub-operations can query to allocate remaining time. Prefer using
asyncio.timeout for enforcement and these helpers for budgeting.
"""

from __future__ import annotations

import contextvars
import time
from contextlib import asynccontextmanager
from typing import Optional


_deadline_ts: contextvars.ContextVar[Optional[float]] = contextvars.ContextVar(
    "android_mcp_deadline_ts", default=None
)


def has_deadline() -> bool:
    """Return True if a deadline is active in the current context."""
    return _deadline_ts.get() is not None


def get_deadline() -> Optional[float]:
    """Get the current absolute deadline timestamp (monotonic), if any."""
    return _deadline_ts.get()


def remaining_time(min_floor: float = 0.05, default: float = 60.0) -> float:
    """Compute remaining seconds until the active deadline.

    If no deadline is set, return `default`. Always returns at least `min_floor`.
    """
    dl = _deadline_ts.get()
    if dl is None:
        return max(min_floor, float(default))
    rem = dl - time.monotonic()
    return max(min_floor, float(rem))


@asynccontextmanager
async def start_deadline(total_seconds: float):
    """Start a deadline window for the current task.

    Use together with `asyncio.timeout(total_seconds)` to enforce the limit
    while allowing sub-operations to budget using `remaining_time()`.
    """
    # Clamp to a small positive duration to avoid zero/negative timeouts
    budget = max(0.05, float(total_seconds))
    token = _deadline_ts.set(time.monotonic() + budget)
    try:
        yield
    finally:
        _deadline_ts.reset(token)


def stage_budget(fraction: float, cap: Optional[float] = None, default: float = 60.0) -> float:
    """Compute a per-stage timeout based on remaining budget.

    - `fraction` is applied to the remaining time (0 < fraction <= 1).
    - If `cap` is provided, the result will not exceed it.
    - If no deadline is active, uses `default` then applies fraction/cap.
    """
    frac = max(0.0, min(1.0, float(fraction))) or 1.0
    rem = remaining_time(default=default)
    value = rem * frac
    if cap is not None:
        value = min(value, float(cap))
    # Ensure a tiny positive budget
    return max(0.05, value)
