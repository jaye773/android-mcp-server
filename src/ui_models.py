"""Data models and utilities for UI inspection."""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class UIElement:
    """Structured representation of UI element."""

    class_name: str
    resource_id: Optional[str]
    text: Optional[str]
    content_desc: Optional[str]
    bounds: Dict[str, int]  # {left, top, right, bottom}
    center: Dict[str, int]  # {x, y}
    clickable: bool
    enabled: bool
    focusable: bool
    scrollable: bool
    displayed: bool
    children: List["UIElement"]
    xpath: str
    index: int


def parse_bounds(bounds_str: str) -> Dict[str, int]:
    """Parse bounds string '[left,top][right,bottom]' to coordinates.

    Returns dict with left, top, right, bottom keys.
    Returns zeroed dict on invalid input.
    """
    try:
        if not bounds_str or bounds_str.strip() == "":
            logger.warning("Empty bounds string provided")
            return {"left": 0, "top": 0, "right": 0, "bottom": 0}

        clean = bounds_str.replace("[", "").replace("]", ",")
        coords = [int(x) for x in clean.split(",") if x.strip()]

        if len(coords) != 4:
            logger.warning(
                f"Expected 4 coordinates in bounds, got {len(coords)}: {bounds_str}"
            )
            return {"left": 0, "top": 0, "right": 0, "bottom": 0}

        left, top, right, bottom = coords

        if left > right or top > bottom:
            logger.warning(
                f"Invalid bounds geometry: left={left}, top={top}, right={right}, bottom={bottom}"
            )
            if left > right:
                left, right = right, left
            if top > bottom:
                top, bottom = bottom, top

        if any(coord < 0 for coord in (left, top, right, bottom)):
            logger.warning(f"Negative coordinates found in bounds: {bounds_str}")
            left, top, right, bottom = (
                max(0, left),
                max(0, top),
                max(0, right),
                max(0, bottom),
            )

        if any(coord > 10000 for coord in (left, top, right, bottom)):
            logger.warning(
                f"Unusually large coordinates found in bounds: {bounds_str}"
            )

        return {"left": left, "top": top, "right": right, "bottom": bottom}

    except (ValueError, IndexError, Exception) as e:
        logger.warning(f"Failed to parse bounds '{bounds_str}': {e}")
        return {"left": 0, "top": 0, "right": 0, "bottom": 0}
