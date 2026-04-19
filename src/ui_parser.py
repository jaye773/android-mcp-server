"""XML parsing helpers for Android UI dumps.

Pure parsing and sanitization logic — no ADB or device communication. The
class :class:`UIParser` converts a raw ``uiautomator`` XML dump into a flat
list of :class:`UIElement` records, with tolerant recovery strategies for
the malformed XML that real-world devices occasionally emit.
"""

from __future__ import annotations

import html
import logging
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

from .ui_models import UIElement, parse_bounds

logger = logging.getLogger(__name__)


def clean_xml_content(xml_content: str) -> str:
    """Strip control characters and invalid bytes from UI-dump XML."""
    # Remove null bytes and other problematic characters
    cleaned = (
        xml_content.replace("\x00", "").replace("\x01", "").replace("\x02", "")
    )

    # Fix common XML encoding issues
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", cleaned)

    # Remove or escape problematic attribute values
    cleaned = re.sub(
        r'text="[^"]*[\x00-\x08\x0B\x0C\x0E-\x1F\x7F][^"]*"', 'text=""', cleaned
    )
    cleaned = re.sub(
        r'content-desc="[^"]*[\x00-\x08\x0B\x0C\x0E-\x1F\x7F][^"]*"',
        'content-desc=""',
        cleaned,
    )

    return cleaned


def escape_xml_content(xml_content: str) -> str:
    """HTML-escape the values of ``text`` and ``content-desc`` attributes."""

    def escape_attribute(match: re.Match) -> str:
        attr_name = match.group(1)
        attr_value = match.group(2)
        escaped_value = html.escape(attr_value, quote=True)
        return f'{attr_name}="{escaped_value}"'

    return re.sub(
        r'(text|content-desc)="([^"]*)"', escape_attribute, xml_content
    )


def parse_element_attributes(element: ET.Element) -> Dict[str, Any]:
    """Parse XML element attributes to a plain dictionary."""
    attrs = element.attrib
    return {
        "text": attrs.get("text", ""),
        "resource-id": attrs.get("resource-id", ""),
        "class": attrs.get("class", ""),
        "content-desc": attrs.get("content-desc", ""),
        "bounds": attrs.get("bounds", "[0,0][0,0]"),
        "clickable": attrs.get("clickable", "false"),
        "enabled": attrs.get("enabled", "true"),
        "focusable": attrs.get("focusable", "false"),
        "scrollable": attrs.get("scrollable", "false"),
        "displayed": attrs.get("displayed", "true"),
    }


class UIParser:
    """Parse a uiautomator XML dump into :class:`UIElement` objects."""

    def parse(
        self, xml_content: str, include_invisible: bool = False
    ) -> List[UIElement]:
        """Parse XML dump into structured UIElement objects (best effort)."""
        try:
            root = ET.fromstring(xml_content)
            elements: List[UIElement] = []
            self._parse_element_recursive(root, elements, "", include_invisible, 0)
            return elements
        except ET.ParseError as e:
            logger.error(f"XML parsing failed: {e}")
            return []

    def parse_safe(
        self, xml_content: str, include_invisible: bool = False
    ) -> Dict[str, Any]:
        """Parse XML dump with comprehensive error handling and recovery."""
        warnings: List[str] = []

        # Pre-validation checks
        if not xml_content or not xml_content.strip():
            return {
                "success": False,
                "error": "Empty or null XML content received",
                "recovery_suggestions": [
                    "Check if UIAutomator dump command executed successfully",
                    "Ensure device screen is active and not in sleep mode",
                    "Try refreshing the UI dump",
                ],
            }

        xml_content = xml_content.strip()

        # Basic XML structure validation
        if not xml_content.startswith("<"):
            return {
                "success": False,
                "error": "XML content does not start with valid XML tag",
                "recovery_suggestions": [
                    "Check if ADB shell command output is being captured correctly",
                    "Verify device file system permissions",
                    "Try running UIAutomator dump manually",
                ],
                "content_preview": (
                    xml_content[:200] + "..." if len(xml_content) > 200 else xml_content
                ),
            }

        # Check for common error messages in XML content
        error_indicators = [
            ("java.lang.RuntimeException", "UIAutomator runtime error occurred"),
            ("permission denied", "Permission denied - check device permissions"),
            ("device not found", "Device connection lost"),
            ("uiautomator not found", "UIAutomator service not available"),
        ]

        for indicator, message in error_indicators:
            if indicator.lower() in xml_content.lower():
                return {
                    "success": False,
                    "error": f"{message}: {indicator} found in output",
                    "recovery_suggestions": [
                        "Check device connection and ADB status",
                        "Ensure UIAutomator service is running",
                        "Try restarting the target application",
                        "Enable developer options and USB debugging",
                    ],
                    "content_preview": (
                        xml_content[:300] + "..."
                        if len(xml_content) > 300
                        else xml_content
                    ),
                }

        # Attempt XML parsing with multiple recovery strategies
        parse_attempts = [
            ("direct", xml_content),
            ("cleaned", clean_xml_content(xml_content)),
            ("escaped", escape_xml_content(xml_content)),
        ]

        last_error = None
        for strategy, content in parse_attempts:
            try:
                root = ET.fromstring(content)
                elements: List[UIElement] = []
                self._parse_element_recursive(root, elements, "", include_invisible, 0)

                result: Dict[str, Any] = {"success": True, "elements": elements}

                if strategy != "direct":
                    warnings.append(
                        f"XML parsing succeeded using '{strategy}' strategy"
                    )
                    result["warnings"] = warnings

                return result

            except ET.ParseError as e:
                last_error = str(e)
                logger.warning(f"XML parsing failed with '{strategy}' strategy: {e}")
                continue
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Unexpected error during XML parsing with '{strategy}' strategy: {e}"
                )
                continue

        # All parsing attempts failed
        return {
            "success": False,
            "error": f"XML parsing failed with all recovery strategies. Last error: {last_error}",
            "recovery_suggestions": [
                "The XML content appears to be malformed or corrupted",
                "Try refreshing the UI dump",
                "Check if the target app is still running and responsive",
                "Restart the app and try again",
                "Check device logs for system errors",
            ],
            "content_preview": (
                xml_content[:500] + "..." if len(xml_content) > 500 else xml_content
            ),
            "parsing_strategies_tried": [strategy for strategy, _ in parse_attempts],
        }

    def _parse_element_recursive(
        self,
        element: ET.Element,
        elements: List[UIElement],
        xpath_prefix: str,
        include_invisible: bool,
        index: int,
    ) -> int:
        """Recursively parse XML elements into flat list + child trees."""
        attrs = element.attrib

        # Skip invisible elements unless requested
        displayed = attrs.get("displayed", "true").lower() == "true"
        if not include_invisible and not displayed:
            return index

        # Parse bounds "[left,top][right,bottom]"
        bounds_str = attrs.get("bounds", "[0,0][0,0]")
        bounds = parse_bounds(bounds_str)

        # Calculate center point
        center = {
            "x": (bounds["left"] + bounds["right"]) // 2,
            "y": (bounds["top"] + bounds["bottom"]) // 2,
        }

        # Build xpath
        tag_name = element.tag
        xpath = f"{xpath_prefix}/{tag_name}[{index}]"

        # Create UIElement
        ui_element = UIElement(
            class_name=attrs.get("class", ""),
            resource_id=attrs.get("resource-id"),
            text=attrs.get("text"),
            content_desc=attrs.get("content-desc"),
            bounds=bounds,
            center=center,
            clickable=attrs.get("clickable", "false").lower() == "true",
            enabled=attrs.get("enabled", "true").lower() == "true",
            focusable=attrs.get("focusable", "false").lower() == "true",
            scrollable=attrs.get("scrollable", "false").lower() == "true",
            displayed=displayed,
            children=[],
            xpath=xpath,
            index=index,
        )

        elements.append(ui_element)

        # Recursively parse children
        child_index = 0
        for child in element:
            child_index = self._parse_element_recursive(
                child, ui_element.children, xpath, include_invisible, child_index
            )
            # Also add children to the main elements list for easier access
            self._add_children_to_main_list(ui_element.children, elements)
            child_index += 1

        return index + 1

    def _add_children_to_main_list(
        self, children: List[UIElement], main_list: List[UIElement]
    ) -> None:
        """Add children recursively to the main elements list."""
        for child in children:
            if child not in main_list:  # Avoid duplicates
                main_list.append(child)
            if child.children:
                self._add_children_to_main_list(child.children, main_list)
