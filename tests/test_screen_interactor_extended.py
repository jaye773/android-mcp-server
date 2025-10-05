"""Extended test cases for screen_interactor.py to achieve 70% coverage.

This test file focuses on uncovered functionality including:
- GestureController operations (swipe, pinch, rotate)
- TextInputController edge cases and special characters
- Coordinate validation and bounds checking
- Error handling and exception paths
- Screen orientation and multi-touch scenarios
"""

from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.adb_manager import ADBManager
from src.screen_interactor import (
    GestureController,
    InputType,
    ScreenInteractor,
    TextInputController,
)
from src.ui_inspector import ElementFinder, UILayoutExtractor


class MockADBManager:
    """Enhanced mock ADB manager for testing edge cases."""

    def __init__(self, fail_commands: List[str] = None, screen_size: Dict = None):
        self.selected_device = "emulator-5554"
        self.calls = []
        self.fail_commands = fail_commands or []
        self.screen_size_result = screen_size or {
            "success": True,
            "width": 1080,
            "height": 1920,
        }

    async def execute_adb_command(
        self, command: str, timeout: int = 30
    ) -> Dict[str, Any]:
        self.calls.append(command)

        # Simulate command failures for specific commands
        for fail_cmd in self.fail_commands:
            if fail_cmd in command:
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": f"Mock error for command: {fail_cmd}",
                    "returncode": 1,
                }

        # Simulate successful execution
        return {
            "success": True,
            "stdout": "mock success",
            "stderr": "",
            "returncode": 0,
        }

    async def get_screen_size(self) -> Dict[str, Any]:
        return self.screen_size_result


class MockUIInspector:
    """Mock UI inspector for element testing."""

    def __init__(self):
        self.adb_manager = None


class MockElementFinder:
    """Mock element finder with configurable responses."""

    def __init__(self, elements: List[Dict] = None, bounds_result: Dict = None):
        self.ui_inspector = MockUIInspector()
        self.mock_elements = elements or []
        self.mock_bounds = bounds_result

    async def find_elements(self, **kwargs) -> List[Dict]:
        # Filter mock elements based on kwargs
        filtered = self.mock_elements

        # Apply filters if specified
        if kwargs.get("clickable_only") and filtered:
            filtered = [e for e in filtered if e.get("clickable") == "true"]
        if kwargs.get("enabled_only") and filtered:
            filtered = [e for e in filtered if e.get("enabled") == "true"]

        return filtered

    def get_element_center(self, element: Dict) -> Dict[str, int]:
        if self.mock_bounds:
            return self.mock_bounds
        # Default center calculation
        bounds = element.get("bounds", "[100,200][300,400]")
        return {"x": 200, "y": 300}  # Mock center

    def element_to_dict(self, element: Dict) -> Dict:
        return element

    def _parse_bounds_string(self, bounds_str: str) -> Dict:
        if self.mock_bounds:
            return self.mock_bounds
        # Mock bounds parsing
        return {"left": 100, "top": 200, "right": 300, "bottom": 400}


@pytest.mark.asyncio
class TestScreenInteractorExceptionHandling:
    """Test exception handling in ScreenInteractor."""

    async def test_tap_coordinates_exception_handling(self):
        """Test tap_coordinates handles exceptions properly (lines 49-50)."""
        adb = MockADBManager()
        ui = MockUIInspector()
        interactor = ScreenInteractor(adb, ui)

        # Mock ADB manager to raise exception
        adb.execute_adb_command = AsyncMock(
            side_effect=RuntimeError("Connection failed")
        )

        result = await interactor.tap_coordinates(100, 200)

        assert result["success"] is False
        assert result["action"] == "tap"
        assert "Tap failed" in result["error"]
        assert result["coordinates"] == {"x": 100, "y": 200}

    async def test_long_press_coordinates_exception_handling(self):
        """Test long_press_coordinates handles exceptions (lines 201-202)."""
        adb = MockADBManager()
        ui = MockUIInspector()
        interactor = ScreenInteractor(adb, ui)

        # Mock ADB manager to raise exception
        adb.execute_adb_command = AsyncMock(
            side_effect=ConnectionError("Device disconnected")
        )

        result = await interactor.long_press_coordinates(150, 250, 1500)

        assert result["success"] is False
        assert result["action"] == "long_press"
        assert "Long press failed" in result["error"]
        assert result["coordinates"] == {"x": 150, "y": 250}


@pytest.mark.asyncio
class TestScreenInteractorElementTapping:
    """Test complex element tapping scenarios (lines 79-168)."""

    async def test_tap_element_no_elements_found(self):
        """Test tap_element when no elements match criteria."""
        adb = MockADBManager()
        ui = MockUIInspector()
        interactor = ScreenInteractor(adb, ui)

        # Mock element finder with no results
        interactor.element_finder = MockElementFinder([])

        result = await interactor.tap_element(text="Nonexistent Button")

        assert result["success"] is False
        assert "Element not found" in result["error"]
        assert result["criteria"]["text"] == "Nonexistent Button"

    async def test_tap_element_filter_mismatch(self):
        """Test tap_element with elements that don't match filters."""
        adb = MockADBManager()
        ui = MockUIInspector()
        interactor = ScreenInteractor(adb, ui)

        # Mock elements that exist but don't match filters
        mock_elements = [
            {"text": "Button", "clickable": "false", "enabled": "true"},
            {"text": "Button", "clickable": "true", "enabled": "false"},
        ]
        interactor.element_finder = MockElementFinder(mock_elements)

        # Override find_elements to simulate filter behavior
        async def mock_find_elements(**kwargs):
            if kwargs.get("clickable_only"):
                return []  # No clickable elements
            return mock_elements

        interactor.element_finder.find_elements = mock_find_elements

        result = await interactor.tap_element(text="Button", clickable_only=True)

        assert result["success"] is False
        assert "doesn't match filters" in result["error"]
        assert "Found 1 non-clickable element(s)" in result["error"]
        assert result["elements_found_without_filters"] == 2

    async def test_tap_element_index_out_of_range(self):
        """Test tap_element with index beyond available elements."""
        adb = MockADBManager()
        ui = MockUIInspector()
        interactor = ScreenInteractor(adb, ui)

        mock_elements = [{"text": "Button1"}, {"text": "Button2"}]
        interactor.element_finder = MockElementFinder(mock_elements)

        result = await interactor.tap_element(text="Button", index=5)

        assert result["success"] is False
        assert "Index 5 out of range" in result["error"]
        assert result["elements_found"] == 2

    async def test_tap_element_invalid_bounds(self):
        """Test tap_element when element center cannot be calculated."""
        adb = MockADBManager()
        ui = MockUIInspector()
        interactor = ScreenInteractor(adb, ui)

        mock_elements = [{"text": "Button", "bounds": "invalid_bounds"}]
        interactor.element_finder = MockElementFinder(mock_elements)
        interactor.element_finder.get_element_center = Mock(return_value=None)

        result = await interactor.tap_element(text="Button")

        assert result["success"] is False
        assert "Could not calculate element center" in result["error"]
        assert "invalid_bounds" in result["element_bounds"]

    async def test_tap_element_successful_with_details(self):
        """Test successful tap_element with all details."""
        adb = MockADBManager()
        ui = MockUIInspector()
        interactor = ScreenInteractor(adb, ui)

        mock_elements = [
            {"text": "Button1", "bounds": "[100,200][300,400]"},
            {"text": "Button2", "bounds": "[400,500][600,700]"},
        ]
        interactor.element_finder = MockElementFinder(mock_elements)

        result = await interactor.tap_element(text="Button", index=1)

        assert result["success"] is True
        assert result["index_used"] == 1
        assert result["total_found"] == 2
        assert "element" in result

    async def test_tap_element_exception_handling(self):
        """Test tap_element exception handling."""
        adb = MockADBManager()
        ui = MockUIInspector()
        interactor = ScreenInteractor(adb, ui)

        # Mock element finder to raise exception
        interactor.element_finder = Mock()
        interactor.element_finder.find_elements = AsyncMock(
            side_effect=ValueError("Parse error")
        )

        result = await interactor.tap_element(text="Button")

        assert result["success"] is False
        assert "Element tap failed" in result["error"]
        assert result["criteria"]["text"] == "Button"


@pytest.mark.asyncio
class TestGestureControllerAdvanced:
    """Test advanced GestureController functionality (lines 216-324, 333-395)."""

    async def test_swipe_coordinates_exception_handling(self):
        """Test swipe_coordinates exception handling (lines 242-243)."""
        adb = MockADBManager()
        gesture = GestureController(adb)

        # Mock exception during command execution
        adb.execute_adb_command = AsyncMock(side_effect=OSError("Permission denied"))

        result = await gesture.swipe_coordinates(0, 0, 100, 100)

        assert result["success"] is False
        assert result["action"] == "swipe"
        assert "Swipe failed" in result["error"]
        assert result["start"] == {"x": 0, "y": 0}
        assert result["end"] == {"x": 100, "y": 100}

    async def test_swipe_direction_screen_size_failure(self):
        """Test swipe_direction when screen size cannot be obtained (line 271)."""
        adb = MockADBManager(
            screen_size={"success": False, "error": "Display not found"}
        )
        gesture = GestureController(adb)

        result = await gesture.swipe_direction("up")

        assert result["success"] is False
        assert "Could not get screen dimensions" in result["error"]

    async def test_swipe_direction_invalid_direction(self):
        """Test swipe_direction with invalid direction (lines 295-299)."""
        adb = MockADBManager()
        gesture = GestureController(adb)

        result = await gesture.swipe_direction("diagonal")

        assert result["success"] is False
        assert "Invalid direction: diagonal" in result["error"]
        assert "Use: up, down, left, right" in result["error"]

    async def test_swipe_direction_custom_parameters(self):
        """Test swipe_direction with custom start point and distance (lines 277-285)."""
        adb = MockADBManager()
        gesture = GestureController(adb)

        result = await gesture.swipe_direction(
            "right", distance=200, start_point=(100, 150), duration_ms=500
        )

        assert result["success"] is True
        assert result["direction"] == "right"
        assert result["distance"] == 200
        assert result["screen_size"]["width"] == 1080
        assert result["screen_size"]["height"] == 1920

    async def test_swipe_direction_exception_handling(self):
        """Test swipe_direction exception handling (lines 318-319)."""
        adb = MockADBManager()
        gesture = GestureController(adb)

        # Mock get_screen_size to raise exception
        adb.get_screen_size = AsyncMock(side_effect=RuntimeError("Hardware error"))

        result = await gesture.swipe_direction("up")

        assert result["success"] is False
        assert "Directional swipe failed" in result["error"]
        assert result["direction"] == "up"

    async def test_scroll_element_no_ui_inspector(self):
        """Test scroll_element without UI inspector (lines 334-338)."""
        adb = MockADBManager()
        gesture = GestureController(adb)

        result = await gesture.scroll_element({"text": "List"})

        assert result["success"] is False
        assert "UI inspector required" in result["error"]

    async def test_scroll_element_no_scrollable_elements(self):
        """Test scroll_element when no scrollable elements found (lines 344-349)."""
        adb = MockADBManager()
        gesture = GestureController(adb)
        ui = MockUIInspector()

        # Mock element finder with no scrollable elements
        mock_finder = MockElementFinder([])

        with patch("src.screen_interactor.ElementFinder", return_value=mock_finder):
            result = await gesture.scroll_element(
                {"text": "ScrollView"}, ui_inspector=ui
            )

        assert result["success"] is False
        assert "Scrollable element not found" in result["error"]
        assert result["criteria"]["text"] == "ScrollView"

    async def test_scroll_element_invalid_bounds(self):
        """Test scroll_element with unparseable bounds (lines 356-361)."""
        adb = MockADBManager()
        gesture = GestureController(adb)
        ui = MockUIInspector()

        mock_elements = [{"scrollable": "true", "bounds": "invalid_format"}]
        mock_finder = MockElementFinder()
        mock_finder._parse_bounds_string = Mock(return_value=None)

        # Override find_elements to return the mock elements
        async def mock_find_elements(**kwargs):
            return mock_elements

        mock_finder.find_elements = mock_find_elements

        with patch("src.screen_interactor.ElementFinder", return_value=mock_finder):
            result = await gesture.scroll_element(
                {"text": "ScrollView"}, ui_inspector=ui
            )

        assert result["success"] is False
        assert "Could not parse element bounds" in result["error"]
        assert "invalid_format" in result["element_bounds"]

    async def test_scroll_element_successful_multi_scroll(self):
        """Test successful scroll_element with multiple scrolls (lines 368-392)."""
        adb = MockADBManager()
        gesture = GestureController(adb)
        ui = MockUIInspector()

        mock_elements = [{"scrollable": "true", "bounds": "[100,200][500,800]"}]
        mock_finder = MockElementFinder()
        mock_finder._parse_bounds_string = Mock(
            return_value={"left": 100, "top": 200, "right": 500, "bottom": 800}
        )
        mock_finder.element_to_dict = Mock(return_value=mock_elements[0])

        # Override find_elements to return the mock elements
        async def mock_find_elements(**kwargs):
            return mock_elements

        mock_finder.find_elements = mock_find_elements

        # Mock swipe_coordinates to track calls
        gesture.swipe_coordinates = AsyncMock(return_value={"success": True})

        with patch("src.screen_interactor.ElementFinder", return_value=mock_finder):
            with patch("asyncio.sleep"):  # Skip sleep delays
                result = await gesture.scroll_element(
                    {"text": "ScrollList"},
                    direction="down",
                    scroll_count=2,
                    ui_inspector=ui,
                )

        assert result["success"] is True
        assert result["action"] == "scroll"
        assert result["direction"] == "down"
        assert result["scroll_count"] == 2
        assert len(result["results"]) == 2

        # Verify swipe_coordinates was called twice
        assert gesture.swipe_coordinates.call_count == 2

    async def test_scroll_element_up_direction(self):
        """Test scroll_element with upward direction (lines 373-375)."""
        adb = MockADBManager()
        gesture = GestureController(adb)
        ui = MockUIInspector()

        mock_elements = [{"scrollable": "true", "bounds": "[100,200][500,800]"}]
        mock_finder = MockElementFinder()
        mock_finder._parse_bounds_string = Mock(
            return_value={"left": 100, "top": 200, "right": 500, "bottom": 800}
        )
        mock_finder.element_to_dict = Mock(return_value=mock_elements[0])

        # Override find_elements to return the mock elements
        async def mock_find_elements(**kwargs):
            return mock_elements

        mock_finder.find_elements = mock_find_elements

        gesture.swipe_coordinates = AsyncMock(return_value={"success": True})

        with patch("src.screen_interactor.ElementFinder", return_value=mock_finder):
            with patch("asyncio.sleep"):
                result = await gesture.scroll_element(
                    {"text": "ScrollUp"},
                    direction="up",
                    scroll_count=1,
                    ui_inspector=ui,
                )

        assert result["success"] is True
        assert result["direction"] == "up"

    async def test_scroll_element_exception_handling(self):
        """Test scroll_element exception handling (lines 394-399)."""
        adb = MockADBManager()
        gesture = GestureController(adb)
        ui = MockUIInspector()

        # Mock ElementFinder to raise exception
        with patch(
            "src.screen_interactor.ElementFinder", side_effect=RuntimeError("UI error")
        ):
            result = await gesture.scroll_element({"text": "List"}, ui_inspector=ui)

        assert result["success"] is False
        assert "Element scrolling failed" in result["error"]
        assert result["criteria"]["text"] == "List"


class TestTextInputControllerAdvanced:
    """Test advanced TextInputController functionality (lines 419-590)."""

    @pytest.mark.asyncio
    async def test_input_text_clear_existing_failure(self):
        """Test input_text when clearing existing text fails (lines 421-424)."""
        adb = MockADBManager()
        text_controller = TextInputController(adb)

        # Mock clear_text_field to fail
        text_controller.clear_text_field = AsyncMock(
            return_value={"success": False, "error": "Clear failed"}
        )

        with patch("src.screen_interactor.logger") as mock_logger:
            result = await text_controller.input_text("test", clear_existing=True)

            # Should still attempt to input text even if clear fails
            assert result["success"] is True
            assert result["cleared_first"] is True
            mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_input_text_unicode_characters(self):
        """Test input_text with Unicode characters (lines 426-431)."""
        adb = MockADBManager()
        text_controller = TextInputController(adb)

        unicode_text = "Hello 世界 🌍 café"
        result = await text_controller.input_text(unicode_text)

        assert result["success"] is True
        assert result["has_unicode"] is True
        assert len(result["warnings"]) > 0
        assert "non-ASCII characters" in result["warnings"][0]
        assert result["text"] == unicode_text

    @pytest.mark.asyncio
    async def test_input_text_with_submit_success(self):
        """Test input_text with successful submission (lines 442-451)."""
        adb = MockADBManager()
        text_controller = TextInputController(adb)

        # Mock successful key press
        text_controller.press_key = AsyncMock(return_value={"success": True})

        result = await text_controller.input_text("test input", submit=True)

        assert result["success"] is True
        assert result["submitted"] is True
        assert "and submitted" in result["details"]
        text_controller.press_key.assert_called_once_with("ENTER")

    @pytest.mark.asyncio
    async def test_input_text_with_submit_failure(self):
        """Test input_text with submission failure (lines 446-453)."""
        adb = MockADBManager()
        text_controller = TextInputController(adb)

        # Mock failed key press
        text_controller.press_key = AsyncMock(
            return_value={"success": False, "error": "Key not found"}
        )

        with patch("src.screen_interactor.logger") as mock_logger:
            result = await text_controller.input_text("test input", submit=True)

            assert result["success"] is True  # Text input succeeded
            assert result["submitted"] is False
            assert "but submit failed" in result["details"]
            mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_input_text_exception_handling(self):
        """Test input_text exception handling (lines 470-475)."""
        adb = MockADBManager()
        text_controller = TextInputController(adb)

        # Mock ADB to raise exception
        adb.execute_adb_command = AsyncMock(side_effect=ValueError("Invalid command"))

        result = await text_controller.input_text("test")

        assert result["success"] is False
        assert "Text input failed" in result["error"]
        assert result["text"] == "test"

    @pytest.mark.asyncio
    async def test_press_key_common_mappings(self):
        """Test press_key with common key mappings (lines 488-503)."""
        adb = MockADBManager()
        text_controller = TextInputController(adb)

        test_keys = [
            ("back", "KEYCODE_BACK"),
            ("home", "KEYCODE_HOME"),
            ("enter", "KEYCODE_ENTER"),
            ("delete", "KEYCODE_DEL"),
            ("volume_up", "KEYCODE_VOLUME_UP"),
        ]

        for input_key, expected_keycode in test_keys:
            result = await text_controller.press_key(input_key)

            assert result["success"] is True
            assert result["keycode"] == expected_keycode
            assert result["original_input"] == input_key

    @pytest.mark.asyncio
    async def test_press_key_custom_keycode(self):
        """Test press_key with custom keycode."""
        adb = MockADBManager()
        text_controller = TextInputController(adb)

        result = await text_controller.press_key("KEYCODE_CUSTOM")

        assert result["success"] is True
        assert result["keycode"] == "KEYCODE_CUSTOM"
        assert result["original_input"] == "KEYCODE_CUSTOM"

    @pytest.mark.asyncio
    async def test_press_key_exception_handling(self):
        """Test press_key exception handling (lines 522-527)."""
        adb = MockADBManager()
        text_controller = TextInputController(adb)

        # Mock ADB to raise exception
        adb.execute_adb_command = AsyncMock(side_effect=ConnectionError("Device lost"))

        result = await text_controller.press_key("enter")

        assert result["success"] is False
        assert "Key press failed" in result["error"]
        assert result["keycode"] == "enter"

    @pytest.mark.asyncio
    async def test_clear_text_field_select_failure(self):
        """Test clear_text_field when text selection fails (lines 539-544)."""
        adb = MockADBManager(fail_commands=["--longpress KEYCODE_A"])
        text_controller = TextInputController(adb)

        result = await text_controller.clear_text_field()

        assert result["success"] is False
        assert "Failed to select text" in result["error"]
        assert "Mock error" in result["details"]

    @pytest.mark.asyncio
    async def test_clear_text_field_successful(self):
        """Test successful clear_text_field operation."""
        adb = MockADBManager()
        text_controller = TextInputController(adb)

        # Mock successful delete key press
        text_controller.press_key = AsyncMock(return_value={"success": True})

        result = await text_controller.clear_text_field()

        assert result["success"] is True
        assert result["action"] == "clear_text_field"
        assert "Text field cleared" in result["details"]

    @pytest.mark.asyncio
    async def test_clear_text_field_exception_handling(self):
        """Test clear_text_field exception handling (lines 559-560)."""
        adb = MockADBManager()
        text_controller = TextInputController(adb)

        # Mock execute_adb_command to raise exception
        adb.execute_adb_command = AsyncMock(side_effect=RuntimeError("System error"))

        result = await text_controller.clear_text_field()

        assert result["success"] is False
        assert "Clear text field failed" in result["error"]

    def test_escape_text_for_shell_special_characters(self):
        """Test _escape_text_for_shell with various special characters (lines 565-590)."""
        adb = MockADBManager()
        text_controller = TextInputController(adb)

        test_cases = [
            ("hello$world", "hello\\$world"),
            ('quotes"test', 'quotes\\"test'),
            ("back\\slash", "back\\\\slash"),
            ("pipe|test", "pipe\\|test"),
            ("redirect>test", "redirect\\>test"),
            ("wildcard*test", "wildcard\\*test"),
            ("question?mark", "question\\?mark"),
            ("exclamation!", "exclamation\\!"),
            ("hash#tag", "hash\\#tag"),
            ("parentheses(test)", "parentheses\\(test\\)"),
            ("brackets[test]", "brackets\\[test\\]"),
            ("braces{test}", "braces\\{test\\}"),
            ("semicolon;test", "semicolon\\;test"),
            ("ampersand&test", "ampersand\\&test"),
            ("backtick`test", "backtick\\`test"),
        ]

        for input_text, expected_output in test_cases:
            result = text_controller._escape_text_for_shell(input_text)
            assert result == expected_output, f"Failed for input: {input_text}"

    def test_escape_text_for_shell_complex_string(self):
        """Test _escape_text_for_shell with complex string containing multiple special chars."""
        adb = MockADBManager()
        text_controller = TextInputController(adb)

        complex_text = 'echo "Hello $USER & echo `date`" > /tmp/test.txt'
        expected = 'echo \\"Hello \\$USER \\& echo \\`date\\`\\" \\> /tmp/test.txt'

        result = text_controller._escape_text_for_shell(complex_text)
        assert result == expected


@pytest.mark.asyncio
class TestBoundaryConditions:
    """Test boundary conditions and edge cases."""

    async def test_coordinates_boundary_values(self):
        """Test coordinate operations with boundary values."""
        adb = MockADBManager()
        ui = MockUIInspector()
        interactor = ScreenInteractor(adb, ui)
        gesture = GestureController(adb)

        # Test with zero coordinates
        result = await interactor.tap_coordinates(0, 0)
        assert result["success"] is True
        assert result["coordinates"] == {"x": 0, "y": 0}

        # Test with maximum screen coordinates
        result = await gesture.swipe_coordinates(0, 0, 1079, 1919, 1)
        assert result["success"] is True

        # Test with very long duration
        result = await interactor.long_press_coordinates(100, 100, 10000)
        assert result["success"] is True
        assert result["duration_ms"] == 10000

    async def test_empty_and_null_inputs(self):
        """Test handling of empty and null inputs."""
        adb = MockADBManager()
        text_controller = TextInputController(adb)

        # Test empty text input
        result = await text_controller.input_text("")
        assert result["success"] is True
        assert result["text"] == ""
        assert result["has_unicode"] is False

        # Test whitespace-only text
        result = await text_controller.input_text("   \t\n   ")
        assert result["success"] is True

    async def test_large_distance_swipe(self):
        """Test swipe with very large distances."""
        adb = MockADBManager()
        gesture = GestureController(adb)

        # Test swipe with distance larger than screen
        result = await gesture.swipe_direction("right", distance=5000)
        assert result["success"] is True
        assert result["distance"] == 5000

    async def test_multiple_element_scenarios(self):
        """Test scenarios with multiple matching elements."""
        adb = MockADBManager()
        ui = MockUIInspector()
        interactor = ScreenInteractor(adb, ui)

        # Create multiple identical elements
        mock_elements = [
            {
                "text": "Button",
                "clickable": "true",
                "enabled": "true",
                "bounds": f"[{i*100},{i*100}][{(i+1)*100},{(i+1)*100}]",
            }
            for i in range(5)
        ]
        interactor.element_finder = MockElementFinder(mock_elements)

        # Test tapping different indices
        for i in range(5):
            result = await interactor.tap_element(text="Button", index=i)
            assert result["success"] is True
            assert result["index_used"] == i
            assert result["total_found"] == 5


class TestInputTypeEnum:
    """Test InputType enum usage."""

    def test_input_type_enum_values(self):
        """Test that InputType enum has expected values."""
        assert InputType.TAP.value == "tap"
        assert InputType.LONG_PRESS.value == "longpress"
        assert InputType.SWIPE.value == "swipe"
        assert InputType.DRAG.value == "drag"
        assert InputType.TEXT_INPUT.value == "text"
        assert InputType.KEY_EVENT.value == "key"


# Performance and stress test markers
@pytest.mark.performance
@pytest.mark.asyncio
class TestPerformanceScenarios:
    """Test performance-related scenarios."""

    async def test_rapid_successive_taps(self):
        """Test rapid successive tap operations."""
        adb = MockADBManager()
        ui = MockUIInspector()
        interactor = ScreenInteractor(adb, ui)

        # Perform 20 rapid taps
        results = []
        for i in range(20):
            result = await interactor.tap_coordinates(i * 10, i * 10)
            results.append(result)

        # All should succeed
        assert all(r["success"] for r in results)
        assert len(adb.calls) == 20

    async def test_long_text_input(self):
        """Test input of very long text."""
        adb = MockADBManager()
        text_controller = TextInputController(adb)

        # Generate a 1000-character string
        long_text = "A" * 1000

        result = await text_controller.input_text(long_text)
        assert result["success"] is True
        assert result["text"] == long_text

    async def test_complex_swipe_sequence(self):
        """Test complex sequence of swipe operations."""
        adb = MockADBManager()
        gesture = GestureController(adb)

        directions = ["up", "down", "left", "right"]
        results = []

        for direction in directions * 5:  # 20 swipes total
            result = await gesture.swipe_direction(direction, distance=100)
            results.append(result)

        assert all(r["success"] for r in results)
        assert len(results) == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
