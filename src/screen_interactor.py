"""Screen interaction capabilities for Android devices."""

import asyncio
import logging
import shlex
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

from .adb_manager import ADBManager, ADBCommands
from .ui_inspector import UILayoutExtractor, ElementFinder

logger = logging.getLogger(__name__)


class InputType(Enum):
    TAP = "tap"
    LONG_PRESS = "longpress"
    SWIPE = "swipe"
    DRAG = "drag"
    TEXT_INPUT = "text"
    KEY_EVENT = "key"


class ScreenInteractor:
    """Handle all screen interaction operations."""

    def __init__(
        self, adb_manager: ADBManager, ui_inspector: UILayoutExtractor
    ) -> None:
        self.adb_manager = adb_manager
        self.ui_inspector = ui_inspector
        self.element_finder = ElementFinder(ui_inspector)

    async def tap_coordinates(self, x: int, y: int) -> Dict[str, Any]:
        """Execute tap at specific coordinates."""
        try:
            command = ADBCommands.TAP.format(device="{device}", x=x, y=y)
            result = await self.adb_manager.execute_adb_command(command)

            return {
                "success": result["success"],
                "action": "tap",
                "coordinates": {"x": x, "y": y},
                "details": (
                    result.get("stderr") if not result["success"] else "Tap executed"
                ),
            }

        except Exception as e:
            return {
                "success": False,
                "action": "tap",
                "error": f"Tap failed: {str(e)}",
                "coordinates": {"x": x, "y": y},
            }

    async def tap_element(
        self,
        text: Optional[str] = None,
        resource_id: Optional[str] = None,
        content_desc: Optional[str] = None,
        index: int = 0,
        clickable_only: bool = False,
        enabled_only: bool = False,
    ) -> Dict[str, Any]:
        """Find and tap UI element.

        Args:
            text: Text to search for in element
            resource_id: Resource ID of element
            content_desc: Content description of element
            index: Index to use if multiple elements match (default: 0)
            clickable_only: Only find clickable elements (default: False for flexibility)
            enabled_only: Only find enabled elements (default: False for flexibility)

        Returns:
            Dict with success status and tap details or error information
        """
        try:
            # Find matching elements with more flexible defaults
            elements = await self.element_finder.find_elements(
                text=text,
                resource_id=resource_id,
                content_desc=content_desc,
                clickable_only=clickable_only,
                enabled_only=enabled_only,
            )

            if not elements:
                # Try to provide more helpful error message
                all_elements = await self.element_finder.find_elements(
                    text=text,
                    resource_id=resource_id,
                    content_desc=content_desc,
                    clickable_only=False,
                    enabled_only=False,
                )

                if all_elements:
                    # Elements exist but don't match the filters
                    non_clickable = [e for e in all_elements if e.get("clickable") == "false"]
                    disabled = [e for e in all_elements if e.get("enabled") == "false"]

                    error_details = []
                    if clickable_only and non_clickable:
                        error_details.append(f"Found {len(non_clickable)} non-clickable element(s)")
                    if enabled_only and disabled:
                        error_details.append(f"Found {len(disabled)} disabled element(s)")

                    error_msg = "Element found but doesn't match filters"
                    if error_details:
                        error_msg += f": {', '.join(error_details)}"
                    error_msg += ". Try with clickable_only=False or enabled_only=False"

                    return {
                        "success": False,
                        "error": error_msg,
                        "criteria": {
                            "text": text,
                            "resource_id": resource_id,
                            "content_desc": content_desc,
                        },
                        "elements_found_without_filters": len(all_elements),
                    }
                else:
                    return {
                        "success": False,
                        "error": "Element not found. Verify the text, resource_id, or content_desc is correct",
                        "criteria": {
                            "text": text,
                            "resource_id": resource_id,
                            "content_desc": content_desc,
                        },
                    }

            if index >= len(elements):
                return {
                    "success": False,
                    "error": f"Index {index} out of range. Found {len(elements)} elements",
                    "elements_found": len(elements),
                }

            # Tap the element at specified index
            element = elements[index]

            # Calculate center coordinates from bounds string
            center = self.element_finder.get_element_center(element)
            if not center:
                return {
                    "success": False,
                    "error": "Could not calculate element center coordinates",
                    "element_bounds": element.get("bounds", "unknown"),
                }

            result = await self.tap_coordinates(center["x"], center["y"])

            result.update(
                {
                    "element": self.element_finder.element_to_dict(element),
                    "index_used": index,
                    "total_found": len(elements),
                }
            )

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Element tap failed: {str(e)}",
                "criteria": {
                    "text": text,
                    "resource_id": resource_id,
                    "content_desc": content_desc,
                },
            }

    async def long_press_coordinates(
        self, x: int, y: int, duration_ms: int = 1000
    ) -> Dict[str, Any]:
        """Execute long press at specific coordinates."""
        try:
            # Long press is implemented as a very short swipe at same coordinates
            command = ADBCommands.SWIPE.format(
                device="{device}", x1=x, y1=y, x2=x, y2=y, duration=duration_ms
            )
            result = await self.adb_manager.execute_adb_command(command)

            return {
                "success": result["success"],
                "action": "long_press",
                "coordinates": {"x": x, "y": y},
                "duration_ms": duration_ms,
                "details": (
                    result.get("stderr")
                    if not result["success"]
                    else "Long press executed"
                ),
            }

        except Exception as e:
            return {
                "success": False,
                "action": "long_press",
                "error": f"Long press failed: {str(e)}",
                "coordinates": {"x": x, "y": y},
            }


class GestureController:
    """Advanced gesture and swipe operations."""

    def __init__(self, adb_manager: ADBManager) -> None:
        self.adb_manager = adb_manager

    async def swipe_coordinates(
        self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300
    ) -> Dict[str, Any]:
        """Execute swipe between two coordinate points."""
        try:
            command = ADBCommands.SWIPE.format(
                device="{device}",
                x1=start_x,
                y1=start_y,
                x2=end_x,
                y2=end_y,
                duration=duration_ms,
            )
            result = await self.adb_manager.execute_adb_command(command)

            return {
                "success": result["success"],
                "action": "swipe",
                "start": {"x": start_x, "y": start_y},
                "end": {"x": end_x, "y": end_y},
                "duration_ms": duration_ms,
                "details": (
                    result.get("stderr") if not result["success"] else "Swipe executed"
                ),
            }

        except Exception as e:
            return {
                "success": False,
                "action": "swipe",
                "error": f"Swipe failed: {str(e)}",
                "start": {"x": start_x, "y": start_y},
                "end": {"x": end_x, "y": end_y},
            }

    async def swipe_direction(
        self,
        direction: str,
        distance: Optional[int] = None,
        start_point: Optional[Tuple[int, int]] = None,
        duration_ms: int = 300,
    ) -> Dict[str, Any]:
        """
        Swipe in specified direction (up, down, left, right).

        Args:
            direction: 'up', 'down', 'left', 'right'
            distance: Swipe distance in pixels (default: screen_size/3)
            start_point: Starting coordinates (default: screen center)
            duration_ms: Swipe duration
        """
        try:
            # Get screen dimensions
            screen_info = await self.adb_manager.get_screen_size()
            if not screen_info["success"]:
                return {"success": False, "error": "Could not get screen dimensions"}

            screen_width: int = screen_info["width"]
            screen_height: int = screen_info["height"]

            # Default start point (screen center)
            if start_point is None:
                start_x: int = screen_width // 2
                start_y: int = screen_height // 2
            else:
                start_x, start_y = start_point

            # Default distance
            if distance is None:
                distance = min(screen_width, screen_height) // 3

            # Calculate end coordinates based on direction
            direction_map = {
                "up": (start_x, start_y - distance),
                "down": (start_x, start_y + distance),
                "left": (start_x - distance, start_y),
                "right": (start_x + distance, start_y),
            }

            if direction.lower() not in direction_map:
                return {
                    "success": False,
                    "error": f"Invalid direction: {direction}. Use: up, down, left, right",
                }

            end_x, end_y = direction_map[direction.lower()]

            # Execute swipe
            result = await self.swipe_coordinates(
                start_x, start_y, end_x, end_y, duration_ms
            )

            result.update(
                {
                    "direction": direction.lower(),
                    "distance": distance,
                    "screen_size": {"width": screen_width, "height": screen_height},
                }
            )

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Directional swipe failed: {str(e)}",
                "direction": direction,
            }

    async def scroll_element(
        self,
        element_criteria: Dict[str, Any],
        direction: str = "down",
        scroll_count: int = 3,
        ui_inspector: Optional[UILayoutExtractor] = None,
    ) -> Dict[str, Any]:
        """Scroll within a specific UI element."""
        try:
            if not ui_inspector:
                return {
                    "success": False,
                    "error": "UI inspector required for element scrolling",
                }

            # Find scrollable element
            finder = ElementFinder(ui_inspector)
            elements = await finder.find_elements(scrollable=True, **element_criteria)

            if not elements:
                return {
                    "success": False,
                    "error": "Scrollable element not found",
                    "criteria": element_criteria,
                }

            element = elements[0]

            # Calculate scroll area within element bounds
            bounds_str = element.get("bounds", "[0,0][0,0]")
            bounds = finder._parse_bounds_string(bounds_str)
            if not bounds:
                return {
                    "success": False,
                    "error": "Could not parse element bounds for scrolling",
                    "element_bounds": bounds_str,
                }

            center_x: int = (bounds["left"] + bounds["right"]) // 2

            # Scroll distance = 70% of element height
            scroll_distance: int = int((bounds["bottom"] - bounds["top"]) * 0.7)

            results: List[Dict[str, Any]] = []
            for i in range(scroll_count):
                if direction.lower() == "down":
                    start_y = bounds["bottom"] - 50
                    end_y = start_y - scroll_distance
                else:  # up
                    start_y = bounds["top"] + 50
                    end_y = start_y + scroll_distance

                swipe_result = await self.swipe_coordinates(
                    center_x, start_y, center_x, end_y, 500
                )
                results.append(swipe_result)

                # Brief pause between scrolls
                await asyncio.sleep(0.5)

            return {
                "success": True,
                "action": "scroll",
                "element": finder.element_to_dict(element),
                "direction": direction,
                "scroll_count": scroll_count,
                "results": results,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Element scrolling failed: {str(e)}",
                "criteria": element_criteria,
            }


class TextInputController:
    """Handle text input and keyboard operations."""

    def __init__(self, adb_manager: ADBManager) -> None:
        self.adb_manager = adb_manager

    async def input_text(
        self, text: str, clear_existing: bool = False, submit: bool = False
    ) -> Dict[str, Any]:
        """
        Input text into currently focused field.

        Args:
            text: Text to input
            clear_existing: Clear field before typing
            submit: Whether to submit the text by pressing Enter
        """
        try:
            # Clear existing text if requested
            if clear_existing:
                clear_result = await self.clear_text_field()
                if not clear_result["success"]:
                    logger.warning(f"Failed to clear text field: {clear_result}")

            # Check for Unicode characters
            has_unicode = any(ord(char) > 127 for char in text)
            warnings = []

            if has_unicode:
                warnings.append("Text contains non-ASCII characters. Standard Android text input may have limitations with Unicode. Consider using a specialized Unicode input method if text appears incorrectly.")

            # Escape special characters for shell
            escaped_text = self._escape_text_for_shell(text)

            command = ADBCommands.TEXT_INPUT.format(
                device="{device}", text=shlex.quote(escaped_text)
            )
            result = await self.adb_manager.execute_adb_command(command)

            # Submit text if requested and input was successful
            submitted = False
            if submit and result["success"]:
                submit_result = await self.press_key("ENTER")
                submitted = submit_result["success"]
                if not submitted:
                    logger.warning(f"Text input succeeded but submit failed: {submit_result}")

            success_message = "Text input successful"
            if submitted:
                success_message += " and submitted"
            elif submit and not submitted:
                success_message += " but submit failed"

            return {
                "success": result["success"],
                "action": "text_input",
                "text": text,
                "cleared_first": clear_existing,
                "submitted": submitted,
                "has_unicode": has_unicode,
                "warnings": warnings,
                "details": (
                    result.get("stderr")
                    if not result["success"]
                    else success_message
                ),
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Text input failed: {str(e)}",
                "text": text,
            }

    async def press_key(self, keycode: str) -> Dict[str, Any]:
        """
        Press device key by keycode or name.

        Common keycodes:
        - BACK, HOME, MENU, SEARCH
        - ENTER, SPACE, DEL
        - VOLUME_UP, VOLUME_DOWN
        """
        try:
            # Map common key names to keycodes
            key_map: Dict[str, str] = {
                "back": "KEYCODE_BACK",
                "home": "KEYCODE_HOME",
                "menu": "KEYCODE_MENU",
                "enter": "KEYCODE_ENTER",
                "space": "KEYCODE_SPACE",
                "delete": "KEYCODE_DEL",
                "del": "KEYCODE_DEL",
                "tab": "KEYCODE_TAB",
                "escape": "KEYCODE_ESCAPE",
                "volume_up": "KEYCODE_VOLUME_UP",
                "volume_down": "KEYCODE_VOLUME_DOWN",
            }

            # Convert common names to official keycodes
            actual_keycode: str = key_map.get(keycode.lower(), keycode)

            command = ADBCommands.KEY_EVENT.format(
                device="{device}", keycode=actual_keycode
            )
            result = await self.adb_manager.execute_adb_command(command)

            return {
                "success": result["success"],
                "action": "key_press",
                "keycode": actual_keycode,
                "original_input": keycode,
                "details": (
                    result.get("stderr")
                    if not result["success"]
                    else f"Key {actual_keycode} pressed"
                ),
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Key press failed: {str(e)}",
                "keycode": keycode,
            }

    async def clear_text_field(self) -> Dict[str, Any]:
        """Clear currently focused text field."""
        try:
            # Use Ctrl+A to select all, then delete
            # On Android, this is typically KEYCODE_A with META
            select_command = (
                "adb -s {device} shell input keyevent --longpress KEYCODE_A"
            )
            select_result = await self.adb_manager.execute_adb_command(select_command)

            if not select_result["success"]:
                return {
                    "success": False,
                    "error": "Failed to select text",
                    "details": select_result.get("stderr"),
                }

            # Delete selected text
            delete_result = await self.press_key("KEYCODE_DEL")

            return {
                "success": delete_result["success"],
                "action": "clear_text_field",
                "details": (
                    "Text field cleared"
                    if delete_result["success"]
                    else "Failed to clear text field"
                ),
            }

        except Exception as e:
            return {"success": False, "error": f"Clear text field failed: {str(e)}"}

    def _escape_text_for_shell(self, text: str) -> str:
        """Escape special characters for shell command."""
        # Replace characters that cause issues in shell
        replacements: Dict[str, str] = {
            "\\": "\\\\",
            '"': '\\"',
            "$": "\\$",
            "`": "\\`",
            "&": "\\&",
            ";": "\\;",
            "|": "\\|",
            "<": "\\<",
            ">": "\\>",
            "(": "\\(",
            ")": "\\)",
            "{": "\\{",
            "}": "\\}",
            "[": "\\[",
            "]": "\\]",
            "*": "\\*",
            "?": "\\?",
            "!": "\\!",
            "#": "\\#",
        }

        for char, escaped in replacements.items():
            text = text.replace(char, escaped)

        return text
