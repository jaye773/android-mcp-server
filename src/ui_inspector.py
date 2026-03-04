"""UI Inspector for Android layout analysis."""

import asyncio
import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from .adb_manager import ADBCommands, ADBManager
from .ui_models import UIElement, parse_bounds

logger = logging.getLogger(__name__)


class UILayoutExtractor:
    """Extract and parse UI layout from uiautomator dump."""

    def __init__(self, adb_manager: ADBManager) -> None:
        """Initialize UILayoutExtractor with ADB manager.

        Args:
            adb_manager: ADBManager instance for device communication.
        """
        self.adb_manager = adb_manager

    async def get_ui_layout(
        self,
        compressed: bool = False,
        include_invisible: bool = False,
        retry_on_failure: bool = True,
        max_retries: int = 3,
        adb_timeout: int | None = None,
    ) -> Dict[str, Any]:
        """Extract complete UI hierarchy with comprehensive error handling.

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
            elements: List[UIElement] = []
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
                elements: List[UIElement] = []
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
        result: List[Dict[str, Any]] = []
        for child in children:
            child_dict: Dict[str, Any] = {
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


# Backward compatibility re-exports
from .element_finder import ElementFinder  # noqa: E402, F401
from .ui_models import UIElement, parse_bounds  # noqa: E402, F401
