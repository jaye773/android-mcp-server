"""Element finding and matching for Android UI."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from .ui_models import parse_bounds

if TYPE_CHECKING:
    from .ui_retriever import UILayoutExtractor

logger = logging.getLogger(__name__)


class ElementFinder:
    """Find UI elements by various criteria."""

    def __init__(self, ui_extractor: UILayoutExtractor) -> None:
        """Initialize ElementFinder with UI layout extractor.

        Args:
            ui_extractor: UILayoutExtractor instance for getting UI layout.
        """
        self.ui_extractor = ui_extractor

    async def find_elements(
        self,
        text: Optional[str] = None,
        resource_id: Optional[str] = None,
        class_name: Optional[str] = None,
        content_desc: Optional[str] = None,
        clickable_only: bool = False,
        enabled_only: bool = True,
        scrollable_only: bool = False,
        exact_match: bool = False,
    ) -> List[Dict[str, Any]]:
        """Find elements matching criteria.

        Returns list of matching UIElement objects.
        """
        try:
            # Get current UI layout
            layout_result = await self.ui_extractor.get_ui_layout()
            if not layout_result["success"]:
                # Return empty immediately if we can't get the UI layout
                return []

            elements = layout_result["elements"]

            # Quick check: if no elements in the layout, return immediately
            if not elements:
                return []

            matches: List[Dict[str, Any]] = []

            self._find_in_elements_recursive(
                elements,
                matches,
                text,
                resource_id,
                class_name,
                content_desc,
                clickable_only,
                enabled_only,
                scrollable_only,
                exact_match,
            )

            # Elements are already dictionaries, return them directly
            return matches

        except Exception as e:
            logger.error(f"Element finding failed: {e}")
            return []

    def _find_in_elements_recursive(
        self,
        elements: List[Dict[str, Any]],
        matches: List[Dict[str, Any]],
        text: Optional[str],
        resource_id: Optional[str],
        class_name: Optional[str],
        content_desc: Optional[str],
        clickable_only: bool,
        enabled_only: bool,
        scrollable_only: bool,
        exact_match: bool,
    ) -> None:
        """Recursively search through element tree."""
        for element in elements:
            if self._element_matches_criteria(
                element,
                text,
                resource_id,
                class_name,
                content_desc,
                clickable_only,
                enabled_only,
                scrollable_only,
                exact_match,
            ):
                matches.append(element)

            # For dictionary elements, children are not nested in the same way
            # They're all in the flat elements list, so no need to recurse through children

    def _element_matches_criteria(
        self,
        element: Dict[str, Any],
        text: Optional[str],
        resource_id: Optional[str],
        class_name: Optional[str],
        content_desc: Optional[str],
        clickable_only: bool,
        enabled_only: bool,
        scrollable_only: bool,
        exact_match: bool,
    ) -> bool:
        """Check if element matches all specified criteria."""
        # Filter by clickable/enabled/scrollable state
        if clickable_only and element.get("clickable", "false") != "true":
            return False
        if enabled_only and element.get("enabled", "true") != "true":
            return False
        if scrollable_only and element.get("scrollable", "false") != "true":
            return False

        # Text matching
        if text is not None:
            element_text = element.get("text", "")
            if exact_match:
                if element_text != text:
                    return False
            else:
                if text.lower() not in element_text.lower():
                    return False

        # Resource ID matching
        if resource_id is not None:
            element_resource_id = element.get("resource-id", "")
            if exact_match:
                if element_resource_id != resource_id:
                    return False
            else:
                if resource_id not in element_resource_id:
                    return False

        # Class name matching
        if class_name is not None:
            element_class = element.get("class", "")
            if exact_match:
                if element_class != class_name:
                    return False
            else:
                if class_name.lower() not in element_class.lower():
                    return False

        # Content description matching
        if content_desc is not None:
            element_content_desc = element.get("content-desc", "")
            if exact_match:
                if element_content_desc != content_desc:
                    return False
            else:
                if content_desc.lower() not in element_content_desc.lower():
                    return False

        return True

    async def find_best_element(
        self, text: Optional[str] = None, **criteria: Any
    ) -> Optional[Dict[str, Any]]:
        """Find best matching element using scoring algorithm.

        Scoring factors:
        - Exact text match: +10 points
        - Partial text match: +5 points
        - Clickable: +3 points
        - Enabled: +2 points
        - Has resource ID: +1 point
        - Larger size: +1 point (if >100px width/height)
        """
        try:
            # Get raw UIElement objects for scoring
            layout_result = await self.ui_extractor.get_ui_layout()
            if not layout_result["success"]:
                return None

            elements = layout_result["elements"]
            raw_matches: List[Dict[str, Any]] = []

            self._find_in_elements_recursive(
                elements,
                raw_matches,
                text,
                criteria.get("resource_id"),
                criteria.get("class_name"),
                criteria.get("content_desc"),
                criteria.get("clickable_only", False),
                criteria.get("enabled_only", True),
                criteria.get("scrollable_only", False),
                criteria.get("exact_match", False),
            )

            if not raw_matches:
                return None

            scored_matches: List[Tuple[int, Dict[str, Any]]] = []
            for element in raw_matches:
                score: int = 0

                # Text matching score
                element_text = element.get("text", "")
                if text and element_text:
                    if element_text.lower() == text.lower():
                        score += 10
                    elif text.lower() in element_text.lower():
                        score += 5

                # Interaction capability
                if element.get("clickable", "false") == "true":
                    score += 3
                if element.get("enabled", "false") == "true":
                    score += 2

                # Element quality indicators
                if element.get("resource-id", ""):
                    score += 1

                # Size bonus for larger elements (likely more important)
                bounds_str = element.get("bounds", "[0,0][0,0]")
                bounds = parse_bounds(bounds_str)
                if bounds:
                    width: int = bounds["right"] - bounds["left"]
                    height: int = bounds["bottom"] - bounds["top"]
                    if width > 100 and height > 100:
                        score += 1

                scored_matches.append((score, element))

            # Return highest scoring element (already a dict)
            scored_matches.sort(key=lambda x: x[0], reverse=True)
            return scored_matches[0][1]

        except Exception as e:
            logger.error(f"Best element finding failed: {e}")
            return None

    async def find_element_by_text(
        self, text: str, exact_match: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Find single element by text content.

        Args:
            text: Text to search for
            exact_match: Whether to match text exactly

        Returns:
            First matching element as dictionary or None
        """
        try:
            elements = await self.find_elements(text=text, exact_match=exact_match)
            return elements[0] if elements else None
        except Exception as e:
            logger.error(f"Find element by text failed: {e}")
            return None

    async def find_element_by_id(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """Find single element by resource ID.

        Args:
            resource_id: Resource ID to search for

        Returns:
            First matching element as dictionary or None
        """
        try:
            elements = await self.find_elements(
                resource_id=resource_id, exact_match=True
            )
            return elements[0] if elements else None
        except Exception as e:
            logger.error(f"Find element by ID failed: {e}")
            return None

    def get_element_center(self, element: Dict[str, Any]) -> Optional[Dict[str, int]]:
        """Calculate element center coordinates.

        Args:
            element: Element dictionary with bounds information

        Returns:
            Dictionary with x, y coordinates or None if invalid bounds
        """
        try:
            bounds_str = element.get("bounds")
            if not bounds_str:
                return None

            bounds = parse_bounds(bounds_str)
            if not bounds or (
                bounds["left"] == 0
                and bounds["top"] == 0
                and bounds["right"] == 0
                and bounds["bottom"] == 0
            ):
                return None

            center_x = (bounds["left"] + bounds["right"]) // 2
            center_y = (bounds["top"] + bounds["bottom"]) // 2

            return {"x": center_x, "y": center_y}

        except Exception as e:
            logger.error(f"Failed to calculate element center: {e}")
            return None

    def element_to_dict(self, element: Dict[str, Any]) -> Dict[str, Any]:
        """Convert element to dictionary representation (elements are already dicts)."""
        # Elements are already dictionaries, but ensure all expected keys are present
        result = dict(element)  # Copy the original dict

        # Ensure all expected keys exist with default values
        expected_keys = {
            "text": "",
            "resource-id": "",
            "class": "",
            "content-desc": "",
            "bounds": "[0,0][0,0]",
            "clickable": "false",
            "enabled": "false",
            "focusable": "false",
            "scrollable": "false",
            "displayed": "true",
        }

        for key, default_value in expected_keys.items():
            if key not in result:
                result[key] = default_value

        return result
