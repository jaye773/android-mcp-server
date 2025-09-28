"""UI Inspector for Android layout analysis."""

import asyncio
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from .adb_manager import ADBManager, ADBCommands

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


class UILayoutExtractor:
    """Extract and parse UI layout from uiautomator dump."""

    def __init__(self, adb_manager: ADBManager) -> None:
        self.adb_manager = adb_manager

    async def get_ui_layout(
        self,
        compressed: bool = False,
        include_invisible: bool = False,
        retry_on_failure: bool = True,
        max_retries: int = 3,
        adb_timeout: int | None = None,
    ) -> Dict[str, Any]:
        """
        Extract complete UI hierarchy with comprehensive error handling.

        Returns:
        {
            "success": bool,
            "elements": List[UIElement],
            "xml_dump": str,
            "stats": {"total_elements": int, "clickable_elements": int},
            "recovery_attempts": List[str],  # Added when recovery was attempted
            "warnings": List[str]  # Added when there are non-fatal issues
        }
        """
        recovery_attempts = []
        warnings = []
        last_error = None

        for attempt in range(max_retries if retry_on_failure else 1):
            try:
                # Get UI dump command
                command = (
                    ADBCommands.UI_DUMP_COMPRESSED
                    if compressed
                    else ADBCommands.UI_DUMP
                )
                # Use a shorter ADB timeout if provided (helps avoid hangs on heavy apps like Chrome)
                result = await self.adb_manager.execute_adb_command(
                    command, timeout=(adb_timeout or 30)
                )

                if not result["success"]:
                    error_msg = result.get("error", "UI dump failed")
                    stderr = result.get("stderr", "")

                    # Analyze specific error conditions
                    if (
                        "uiautomator" in stderr.lower()
                        and "not found" in stderr.lower()
                    ):
                        recovery_msg = "UIAutomator service not available. Try enabling developer options."
                    elif "permission denied" in stderr.lower():
                        recovery_msg = "Permission denied. Check ADB permissions and USB debugging."
                    elif "device offline" in stderr.lower():
                        recovery_msg = "Device offline. Reconnect device and try again."
                    else:
                        recovery_msg = f"UI dump command failed: {error_msg}"

                    if attempt < max_retries - 1 and retry_on_failure:
                        recovery_attempts.append(
                            f"Attempt {attempt + 1}: {recovery_msg} - Retrying..."
                        )
                        # Try with different compression setting
                        compressed = not compressed
                        await asyncio.sleep(1)
                        continue
                    else:
                        return {
                            "success": False,
                            "error": recovery_msg,
                            "recovery_attempts": recovery_attempts,
                            "recovery_suggestions": [
                                "Ensure device is unlocked and USB debugging is enabled",
                                "Try disconnecting and reconnecting the device",
                                "Check if UIAutomator service is running",
                                "Restart ADB server: 'adb kill-server && adb start-server'",
                            ],
                        }

                # Pull XML file from device with retry logic
                xml_content = await self._pull_ui_dump_file_with_retry(
                    adb_timeout=adb_timeout
                )
                if not xml_content:
                    if attempt < max_retries - 1 and retry_on_failure:
                        recovery_attempts.append(
                            f"Attempt {attempt + 1}: Failed to retrieve UI dump - Retrying..."
                        )
                        await asyncio.sleep(1)
                        continue
                    else:
                        return {
                            "success": False,
                            "error": "Failed to retrieve UI dump file from device",
                            "recovery_attempts": recovery_attempts,
                            "recovery_suggestions": [
                                "Check if /sdcard/ is accessible on the device",
                                "Ensure sufficient storage space on device",
                                "Verify ADB shell access is working",
                                "Try manually running: adb shell uiautomator dump",
                            ],
                        }

                # Parse XML to structured elements with enhanced error handling
                parse_result = await self._parse_xml_to_elements_safe(
                    xml_content, include_invisible
                )

                if not parse_result["success"]:
                    if attempt < max_retries - 1 and retry_on_failure:
                        recovery_attempts.append(
                            f"Attempt {attempt + 1}: {parse_result['error']} - Retrying..."
                        )
                        await asyncio.sleep(1)
                        continue
                    else:
                        return {
                            "success": False,
                            "error": parse_result["error"],
                            "recovery_attempts": recovery_attempts,
                            "recovery_suggestions": parse_result.get(
                                "recovery_suggestions", []
                            ),
                            "xml_preview": (
                                xml_content[:500] + "..." if xml_content else None
                            ),
                        }

                elements = parse_result["elements"]
                if parse_result.get("warnings"):
                    warnings.extend(parse_result["warnings"])

                # Convert UIElement objects to dictionaries for consistency
                elements_dict = []
                for element in elements:
                    element_dict = {
                        "text": element.text or "",
                        "resource-id": element.resource_id or "",
                        "class": element.class_name,
                        "content-desc": element.content_desc or "",
                        "bounds": f"[{element.bounds['left']},{element.bounds['top']}][{element.bounds['right']},{element.bounds['bottom']}]",
                        "clickable": "true" if element.clickable else "false",
                        "enabled": "true" if element.enabled else "false",
                        "focusable": "true" if element.focusable else "false",
                        "scrollable": "true" if element.scrollable else "false",
                        "displayed": "true" if element.displayed else "false",
                    }
                    elements_dict.append(element_dict)

                result_dict = {
                    "success": True,
                    "elements": elements_dict,
                    "xml_dump": xml_content,
                    "stats": self._calculate_stats(elements),
                    "element_count": self._calculate_stats(elements)["total_elements"],
                }

                if recovery_attempts:
                    result_dict["recovery_attempts"] = recovery_attempts
                if warnings:
                    result_dict["warnings"] = warnings

                return result_dict

            except Exception as e:
                last_error = str(e)
                logger.error(
                    f"UI layout extraction failed (attempt {attempt + 1}): {e}"
                )

                if attempt < max_retries - 1 and retry_on_failure:
                    recovery_attempts.append(
                        f"Attempt {attempt + 1}: Unexpected error: {last_error} - Retrying..."
                    )
                    await asyncio.sleep(1)
                    continue

        # Final failure after all retries
        return {
            "success": False,
            "error": f"UI layout extraction failed after {max_retries} attempts: {last_error}",
            "recovery_attempts": recovery_attempts,
            "recovery_suggestions": [
                "Check device connection and ADB status",
                "Ensure device is unlocked and responsive",
                "Try restarting the target application",
                "Restart ADB: 'adb kill-server && adb start-server'",
                "Check device logs for system errors",
            ],
        }

    async def _pull_ui_dump_file(self) -> Optional[str]:
        """Pull UI dump file from device."""
        try:
            # UI dump is saved to /sdcard/window_dump.xml
            device_path = "/sdcard/window_dump.xml"

            # Use cat to read the file content directly
            result = await self.adb_manager.execute_adb_command(
                f"adb -s {{device}} shell cat {device_path}"
            )

            if result["success"] and result["stdout"].strip():
                return result["stdout"]

            logger.error(f"Failed to read UI dump: {result}")
            return None

        except Exception as e:
            logger.error(f"Failed to pull UI dump file: {e}")
            return None

    async def _pull_ui_dump_file_with_retry(
        self, max_attempts: int = 3, adb_timeout: int | None = None
    ) -> Optional[str]:
        """Pull UI dump file from device with retry logic and enhanced error handling."""
        device_path = "/sdcard/window_dump.xml"

        for attempt in range(max_attempts):
            try:
                # First, check if file exists
                check_result = await self.adb_manager.execute_adb_command(
                    f"adb -s {{device}} shell test -f {device_path} && echo 'exists' || echo 'missing'",
                    timeout=(adb_timeout or 10),
                )

                if check_result["success"]:
                    if "missing" in check_result["stdout"]:
                        logger.warning(
                            f"UI dump file not found at {device_path} (attempt {attempt + 1})"
                        )
                        if attempt < max_attempts - 1:
                            await asyncio.sleep(0.5)  # Wait for file to be created
                            continue
                        return None

                # Try to read the file content
                result = await self.adb_manager.execute_adb_command(
                    f"adb -s {{device}} shell cat {device_path}",
                    timeout=(adb_timeout or 10),
                )

                if result["success"] and result["stdout"].strip():
                    content = result["stdout"].strip()

                    # Basic validation of XML content
                    if not content.startswith("<") or not content.endswith(">"):
                        logger.warning(
                            f"UI dump content appears malformed (attempt {attempt + 1})"
                        )
                        if attempt < max_attempts - 1:
                            await asyncio.sleep(0.5)
                            continue

                    # Check for minimum content length
                    if len(content) < 100:
                        logger.warning(
                            f"UI dump content too short: {len(content)} characters (attempt {attempt + 1})"
                        )
                        if attempt < max_attempts - 1:
                            await asyncio.sleep(0.5)
                            continue

                    return content
                else:
                    logger.warning(
                        f"Failed to read UI dump (attempt {attempt + 1}): {result}"
                    )

            except Exception as e:
                logger.warning(
                    f"Error pulling UI dump file (attempt {attempt + 1}): {e}"
                )

            if attempt < max_attempts - 1:
                await asyncio.sleep(0.5)

        return None

    async def _parse_xml_to_elements(
        self, xml_content: str, include_invisible: bool = False
    ) -> List[UIElement]:
        """Parse XML dump into structured UIElement objects."""
        try:
            root = ET.fromstring(xml_content)
            elements = []
            self._parse_element_recursive(root, elements, "", include_invisible, 0)
            return elements
        except ET.ParseError as e:
            logger.error(f"XML parsing failed: {e}")
            return []

    async def _parse_xml_to_elements_safe(
        self, xml_content: str, include_invisible: bool = False
    ) -> Dict[str, Any]:
        """Parse XML dump with comprehensive error handling and recovery attempts."""
        warnings = []

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
            ("cleaned", self._clean_xml_content(xml_content)),
            ("escaped", self._escape_xml_content(xml_content)),
        ]

        last_error = None
        for strategy, content in parse_attempts:
            try:
                root = ET.fromstring(content)
                elements = []
                self._parse_element_recursive(root, elements, "", include_invisible, 0)

                result = {"success": True, "elements": elements}

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

    def _clean_xml_content(self, xml_content: str) -> str:
        """Clean XML content by removing problematic characters and fixing common issues."""
        import re

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

    def _escape_xml_content(self, xml_content: str) -> str:
        """Attempt to escape problematic XML content."""
        import html

        # Find and escape unescaped content within attributes
        import re

        def escape_attribute(match):
            attr_name = match.group(1)
            attr_value = match.group(2)
            # Escape the attribute value
            escaped_value = html.escape(attr_value, quote=True)
            return f'{attr_name}="{escaped_value}"'

        # Fix common problematic attributes
        escaped = re.sub(
            r'(text|content-desc)="([^"]*)"', escape_attribute, xml_content
        )

        return escaped

    def _parse_element_recursive(
        self,
        element: ET.Element,
        elements: List[UIElement],
        xpath_prefix: str,
        include_invisible: bool,
        index: int,
    ) -> int:
        """Recursively parse XML elements."""
        attrs = element.attrib

        # Skip invisible elements unless requested
        displayed = attrs.get("displayed", "true").lower() == "true"
        if not include_invisible and not displayed:
            return index

        # Parse bounds "[left,top][right,bottom]"
        bounds_str = attrs.get("bounds", "[0,0][0,0]")
        bounds = self._parse_bounds(bounds_str)

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

    def _parse_bounds(self, bounds_str: str) -> Dict[str, int]:
        """Parse bounds string '[left,top][right,bottom]' to coordinates with enhanced error handling."""
        try:
            # Handle empty or null bounds
            if not bounds_str or bounds_str.strip() == "":
                logger.warning("Empty bounds string provided")
                return {"left": 0, "top": 0, "right": 0, "bottom": 0}

            # Remove brackets and split
            clean = bounds_str.replace("[", "").replace("]", ",")
            coords = [int(x) for x in clean.split(",") if x.strip()]

            # Validate we have exactly 4 coordinates
            if len(coords) != 4:
                logger.warning(
                    f"Expected 4 coordinates in bounds, got {len(coords)}: {bounds_str}"
                )
                return {"left": 0, "top": 0, "right": 0, "bottom": 0}

            # Validate coordinate values make sense
            left, top, right, bottom = coords
            if left > right or top > bottom:
                logger.warning(
                    f"Invalid bounds geometry: left={left}, top={top}, right={right}, bottom={bottom}"
                )
                # Swap if needed
                if left > right:
                    left, right = right, left
                if top > bottom:
                    top, bottom = bottom, top

            # Validate coordinates are reasonable (not negative, not extremely large)
            if any(coord < 0 for coord in coords):
                logger.warning(f"Negative coordinates found in bounds: {bounds_str}")
                coords = [max(0, coord) for coord in coords]
                left, top, right, bottom = coords

            if any(coord > 10000 for coord in coords):
                logger.warning(
                    f"Unusually large coordinates found in bounds: {bounds_str}"
                )

            return {"left": left, "top": top, "right": right, "bottom": bottom}

        except ValueError as e:
            logger.warning(
                f"Failed to parse bounds - invalid numbers in '{bounds_str}': {e}"
            )
            return {"left": 0, "top": 0, "right": 0, "bottom": 0}
        except IndexError as e:
            logger.warning(
                f"Failed to parse bounds - insufficient coordinates in '{bounds_str}': {e}"
            )
            return {"left": 0, "top": 0, "right": 0, "bottom": 0}
        except Exception as e:
            logger.warning(f"Unexpected error parsing bounds '{bounds_str}': {e}")
            return {"left": 0, "top": 0, "right": 0, "bottom": 0}

    def _calculate_stats(self, elements: List[UIElement]) -> Dict[str, int]:
        """Calculate statistics for UI elements."""
        total = 0
        clickable = 0

        def count_recursive(element_list: List[UIElement]) -> None:
            nonlocal total, clickable
            for element in element_list:
                total += 1
                if element.clickable:
                    clickable += 1
                count_recursive(element.children)

        count_recursive(elements)

        return {"total_elements": total, "clickable_elements": clickable}

    async def extract_ui_hierarchy(self) -> Dict[str, Any]:
        """Extract UI hierarchy structure.

        Returns:
        {
            "success": bool,
            "hierarchy": dict,
            "total_elements": int
        }
        """
        try:
            layout_result = await self.get_ui_layout()
            if not layout_result["success"]:
                return {
                    "success": False,
                    "error": layout_result.get("error", "Failed to get UI layout"),
                }

            elements = layout_result["elements"]
            # Note: elements are now dictionaries, not UIElement objects
            hierarchy = self._build_hierarchy_dict_from_dicts(elements)

            return {
                "success": True,
                "hierarchy": hierarchy,
                "total_elements": len(elements),
            }

        except Exception as e:
            logger.error(f"UI hierarchy extraction failed: {e}")
            return {"success": False, "error": str(e)}

    def _build_hierarchy_dict(self, elements: List[UIElement]) -> Dict[str, Any]:
        """Build hierarchical dictionary from flat element list."""
        if not elements:
            return {}

        # For simplicity, return the root element with its children
        root_element = elements[0]
        return {
            "class": root_element.class_name,
            "resource-id": root_element.resource_id,
            "text": root_element.text,
            "bounds": root_element.bounds,
            "children": self._build_children_dict(root_element.children),
        }

    def _build_children_dict(self, children: List[UIElement]) -> List[Dict[str, Any]]:
        """Build children dictionary recursively."""
        result = []
        for child in children:
            child_dict = {
                "class": child.class_name,
                "resource-id": child.resource_id,
                "text": child.text,
                "bounds": child.bounds,
                "clickable": child.clickable,
                "enabled": child.enabled,
            }
            if child.children:
                child_dict["children"] = self._build_children_dict(child.children)
            result.append(child_dict)
        return result

    def _build_hierarchy_dict_from_dicts(
        self, elements: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build hierarchical dictionary from dictionary elements."""
        if not elements:
            return {}

        # For simplicity, return the first element as root
        root_element = elements[0]
        return {
            "class": root_element.get("class", ""),
            "resource-id": root_element.get("resource-id", ""),
            "text": root_element.get("text", ""),
            "bounds": root_element.get("bounds", ""),
            "children": elements[1:] if len(elements) > 1 else [],
        }

    def parse_element_attributes(self, element: ET.Element) -> Dict[str, Any]:
        """Parse XML element attributes to dictionary.

        Args:
            element: XML Element from parsed UI dump

        Returns:
            Dictionary containing parsed attributes
        """
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

    def parse_bounds(self, bounds_str: str) -> Optional[Dict[str, int]]:
        """Parse bounds string to coordinates dictionary.

        Args:
            bounds_str: Bounds in format '[x1,y1][x2,y2]'

        Returns:
            Dictionary with left, top, right, bottom coordinates or None if invalid
        """
        try:
            return self._parse_bounds(bounds_str)
        except Exception as e:
            logger.warning(f"Failed to parse bounds '{bounds_str}': {e}")
            return None


class ElementFinder:
    """Find UI elements by various criteria."""

    def __init__(self, ui_extractor: UILayoutExtractor) -> None:
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
        """
        Find elements matching criteria.

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

            matches = []

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
    ) -> Optional[UIElement]:
        """
        Find best matching element using scoring algorithm.

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
            raw_matches = []

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
                # Parse bounds string to get dimensions
                bounds_str = element.get("bounds", "[0,0][0,0]")
                bounds = self._parse_bounds_string(bounds_str)
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

            # Parse bounds string "[x1,y1][x2,y2]" directly
            bounds = self._parse_bounds_string(bounds_str)
            if not bounds:
                return None

            center_x = (bounds["left"] + bounds["right"]) // 2
            center_y = (bounds["top"] + bounds["bottom"]) // 2

            return {"x": center_x, "y": center_y}

        except Exception as e:
            logger.error(f"Failed to calculate element center: {e}")
            return None

    def _parse_bounds_string(self, bounds_str: str) -> Optional[Dict[str, int]]:
        """Parse bounds string to coordinates dictionary."""
        try:
            # Handle empty or null bounds
            if not bounds_str or bounds_str.strip() == "":
                return None

            # Remove brackets and split
            clean = bounds_str.replace("[", "").replace("]", ",")
            coords = [int(x) for x in clean.split(",") if x.strip()]

            # Validate we have exactly 4 coordinates
            if len(coords) != 4:
                return None

            left, top, right, bottom = coords
            return {"left": left, "top": top, "right": right, "bottom": bottom}

        except (ValueError, IndexError):
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
