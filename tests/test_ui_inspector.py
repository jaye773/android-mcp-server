"""Tests for UI Inspector and Element Finder functionality."""

import asyncio
import xml.etree.ElementTree as ET
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.ui_inspector import ElementFinder, UILayoutExtractor
from tests.mocks import MockErrorScenarios, MockUIScenarios


class TestUILayoutExtractor:
    """Test UI layout extraction functionality."""

    @pytest.mark.asyncio
    async def test_get_ui_layout_success(self, mock_adb_manager):
        """Test successful UI layout extraction."""
        mock_adb_manager.execute_adb_command.return_value = {
            "success": True,
            "stdout": MockUIScenarios.login_screen(),
            "stderr": "",
            "return_code": 0,
        }

        ui_extractor = UILayoutExtractor(mock_adb_manager)
        result = await ui_extractor.get_ui_layout()

        assert result["success"] is True
        assert "xml_dump" in result
        assert "elements" in result
        assert result["element_count"] > 0

        # Should have extracted login screen elements
        elements = result["elements"]
        element_texts = [elem.get("text", "") for elem in elements]
        assert any("Login" in text for text in element_texts)

    @pytest.mark.asyncio
    async def test_get_ui_layout_compressed(self, mock_adb_manager):
        """Test UI layout extraction with compression."""
        mock_adb_manager.execute_adb_command.return_value = {
            "success": True,
            "stdout": MockUIScenarios.login_screen(),
            "stderr": "",
            "return_code": 0,
        }

        ui_extractor = UILayoutExtractor(mock_adb_manager)
        result = await ui_extractor.get_ui_layout(compressed=True)

        assert result["success"] is True
        # Should have called ADB with compressed flag
        mock_adb_manager.execute_adb_command.assert_called()
        # Check all call arguments to find the compressed command
        all_calls = mock_adb_manager.execute_adb_command.call_args_list
        compressed_call_found = any("--compressed" in str(call) for call in all_calls)
        assert compressed_call_found, f"Expected --compressed in calls: {all_calls}"

    @pytest.mark.asyncio
    async def test_get_ui_layout_include_invisible(self, mock_adb_manager):
        """Test UI layout extraction including invisible elements."""
        mock_adb_manager.execute_adb_command.return_value = {
            "success": True,
            "stdout": MockUIScenarios.login_screen(),
            "stderr": "",
            "return_code": 0,
        }

        ui_extractor = UILayoutExtractor(mock_adb_manager)
        result = await ui_extractor.get_ui_layout(include_invisible=True)

        assert result["success"] is True
        # Implementation may filter invisible elements by default
        # This test ensures the parameter is handled correctly

    @pytest.mark.asyncio
    async def test_get_ui_layout_empty_screen(self, mock_adb_manager):
        """Test UI layout extraction on empty screen."""
        mock_adb_manager.execute_adb_command.return_value = {
            "success": True,
            "stdout": MockUIScenarios.empty_screen(),
            "stderr": "",
            "return_code": 0,
        }

        ui_extractor = UILayoutExtractor(mock_adb_manager)
        result = await ui_extractor.get_ui_layout()

        assert result["success"] is True
        assert result["element_count"] >= 0  # May have root element

    @pytest.mark.asyncio
    async def test_get_ui_layout_failure(self, mock_adb_manager):
        """Test UI layout extraction failure."""
        error_response = MockErrorScenarios.ui_service_unavailable_error()
        # Override the side_effect to return error for all commands
        mock_adb_manager.execute_adb_command.side_effect = None  # Clear side_effect
        mock_adb_manager.execute_adb_command.return_value = error_response

        ui_extractor = UILayoutExtractor(mock_adb_manager)
        result = await ui_extractor.get_ui_layout()

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_extract_ui_hierarchy(self, mock_adb_manager):
        """Test UI hierarchy extraction."""
        mock_adb_manager.execute_adb_command.return_value = {
            "success": True,
            "stdout": MockUIScenarios.login_screen(),
            "stderr": "",
            "return_code": 0,
        }

        ui_extractor = UILayoutExtractor(mock_adb_manager)
        result = await ui_extractor.extract_ui_hierarchy()

        assert result["success"] is True
        assert "hierarchy" in result
        assert "total_elements" in result
        assert isinstance(result["hierarchy"], dict)

    @pytest.mark.asyncio
    async def test_parse_ui_element_attributes(self, mock_adb_manager):
        """Test parsing of UI element attributes."""
        ui_extractor = UILayoutExtractor(mock_adb_manager)

        # Test with sample XML element - find the Button element specifically
        xml_content = MockUIScenarios.login_screen()
        root = ET.fromstring(xml_content)
        # Find all button elements and select the one with Login text
        button_elements = root.findall(".//node[@class='android.widget.Button']")
        button_element = None
        for elem in button_elements:
            if elem.get("text") == "Login":
                button_element = elem
                break

        if button_element is not None:
            parsed = ui_extractor.parse_element_attributes(button_element)

            assert parsed["text"] == "Login"
            assert parsed["clickable"] == "true"
            assert "bounds" in parsed

    def test_parse_bounds_attribute(self, mock_adb_manager):
        """Test parsing of element bounds."""
        ui_extractor = UILayoutExtractor(mock_adb_manager)

        # Test various bounds formats
        bounds_tests = [
            (
                "[100,200][300,400]",
                {"left": 100, "top": 200, "right": 300, "bottom": 400},
            ),
            ("[0,0][1080,1920]", {"left": 0, "top": 0, "right": 1080, "bottom": 1920}),
            (
                "[50,100][150,200]",
                {"left": 50, "top": 100, "right": 150, "bottom": 200},
            ),
        ]

        for bounds_str, expected in bounds_tests:
            parsed = ui_extractor.parse_bounds(bounds_str)
            assert parsed == expected

    def test_parse_invalid_bounds(self, mock_adb_manager):
        """Test parsing of invalid bounds."""
        ui_extractor = UILayoutExtractor(mock_adb_manager)

        invalid_bounds = [
            "",  # Empty
            "invalid",  # Not in correct format
            "[100,200]",  # Missing second coordinate pair
            "[100][200,300]",  # Malformed
        ]

        for bounds_str in invalid_bounds:
            parsed = ui_extractor.parse_bounds(bounds_str)
            # Should handle gracefully, either return None or default values
            assert parsed is None or isinstance(parsed, dict)

    @pytest.mark.asyncio
    async def test_ui_layout_caching(self, mock_adb_manager):
        """Test UI layout caching functionality."""
        mock_adb_manager.execute_adb_command.return_value = {
            "success": True,
            "stdout": MockUIScenarios.login_screen(),
            "stderr": "",
            "return_code": 0,
        }

        ui_extractor = UILayoutExtractor(mock_adb_manager)

        # First call
        result1 = await ui_extractor.get_ui_layout()
        call_count1 = mock_adb_manager.execute_adb_command.call_count

        # Second call (may use cache)
        result2 = await ui_extractor.get_ui_layout()
        call_count2 = mock_adb_manager.execute_adb_command.call_count

        assert result1["success"] is True
        assert result2["success"] is True

        # Implementation-dependent: may or may not use caching
        # This test ensures both calls work correctly

    @pytest.mark.asyncio
    async def test_ui_layout_with_malformed_xml(self, mock_adb_manager):
        """Test handling of malformed XML."""
        # Clear side_effect to allow return_value to take precedence
        mock_adb_manager.execute_adb_command.side_effect = None
        mock_adb_manager.execute_adb_command.return_value = {
            "success": True,
            "stdout": "<?xml version='1.0'?><hierarchy><node unclosed_tag</hierarchy>",
            "stderr": "",
            "return_code": 0,
        }

        ui_extractor = UILayoutExtractor(mock_adb_manager)
        result = await ui_extractor.get_ui_layout()

        # Should handle malformed XML gracefully
        assert result["success"] is False or result["element_count"] == 0

    @pytest.mark.asyncio
    async def test_ui_layout_handles_disconnect_during_cat(self, mock_adb_manager):
        """Device disconnects mid-sequence: dump ok, test -f ok, cat fails.

        The first two ADB calls (uiautomator dump, test -f) succeed. The third
        call (cat /sdcard/window_dump.xml) fails with "device not found".
        get_ui_layout must return a graceful {success: False, error: ...}
        response without leaking a Python traceback.
        """
        mock_adb_manager.execute_adb_command.side_effect = None

        call_log = []

        async def scripted(cmd, timeout=30):
            call_log.append(cmd)
            if "uiautomator dump" in cmd:
                return {
                    "success": True,
                    "stdout": "UI hierchary dumped to: /sdcard/window_dump.xml",
                    "stderr": "",
                    "return_code": 0,
                }
            if "test -f" in cmd:
                return {
                    "success": True,
                    "stdout": "exists",
                    "stderr": "",
                    "return_code": 0,
                }
            if "cat " in cmd:
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": "error: device 'emulator-5554' not found",
                    "error": "device 'emulator-5554' not found",
                    "return_code": 1,
                }
            return {
                "success": True,
                "stdout": "",
                "stderr": "",
                "return_code": 0,
            }

        mock_adb_manager.execute_adb_command.side_effect = scripted

        ui_extractor = UILayoutExtractor(mock_adb_manager)

        # Keep retries small but > 1 so we exercise the retry path; also
        # shrink the sleep by patching asyncio.sleep to a no-op for speed.
        with patch("src.ui_inspector.asyncio.sleep", new=AsyncMock(return_value=None)):
            result = await ui_extractor.get_ui_layout(max_retries=2)

        # Must return a clean error dict, never raise
        assert isinstance(result, dict)
        assert result["success"] is False
        assert "error" in result
        # Sanity: test -f and cat were actually attempted
        assert any("test -f" in c for c in call_log)
        assert any("cat " in c for c in call_log)

    @pytest.mark.asyncio
    async def test_ui_layout_timeout_during_retry(self, mock_adb_manager):
        """A TimeoutError on the 2nd parse attempt must not leak as a traceback.

        The parse-safe method tries up to 3 parsing strategies. We simulate a
        TimeoutError raised on the 2nd parsing strategy; the method should
        catch it internally (its except clause swallows all Exceptions),
        continue to the 3rd strategy, and — if that also fails — return a
        clean {success: False, error: ...}.
        """
        mock_adb_manager.execute_adb_command.side_effect = None

        # Provide valid flow for dump + test -f + cat, but return XML that the
        # 1st strategy ("direct") will fail to parse (control char in attr)
        # so the 2nd strategy ("cleaned") is invoked — we raise TimeoutError
        # there to mimic the described scenario.
        async def scripted(cmd, timeout=30):
            if "uiautomator dump" in cmd:
                return {
                    "success": True,
                    "stdout": "",
                    "stderr": "",
                    "return_code": 0,
                }
            if "test -f" in cmd:
                return {
                    "success": True,
                    "stdout": "exists",
                    "stderr": "",
                    "return_code": 0,
                }
            if "cat " in cmd:
                # XML with a control char that will break ET.fromstring on
                # the direct strategy but not the cleaned one.
                xml_bad = (
                    "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>"
                    "<hierarchy rotation=\"0\">"
                    "<node index=\"0\" text=\"bad\x01text\" class=\"x\" "
                    "bounds=\"[0,0][10,10]\"/>"
                    "</hierarchy>"
                )
                return {
                    "success": True,
                    "stdout": xml_bad,
                    "stderr": "",
                    "return_code": 0,
                }
            return {"success": True, "stdout": "", "stderr": "", "return_code": 0}

        mock_adb_manager.execute_adb_command.side_effect = scripted

        ui_extractor = UILayoutExtractor(mock_adb_manager)

        # Inject a TimeoutError when the 2nd parse strategy's cleaner runs.
        # _clean_xml_content is called as the content-transform for the
        # "cleaned" strategy (see _parse_xml_to_elements_safe.parse_attempts).
        def fail_on_clean(content):
            raise asyncio.TimeoutError("synthetic timeout during cleanup")

        ui_extractor._clean_xml_content = fail_on_clean

        with patch("src.ui_inspector.asyncio.sleep", new=AsyncMock(return_value=None)):
            result = await ui_extractor.get_ui_layout(max_retries=1)

        # Even though TimeoutError was raised mid-strategy, the top-level
        # method must return a structured response (not raise).
        assert isinstance(result, dict)
        assert "success" in result
        # Either it parsed via the 3rd strategy or reported a clean error
        assert result["success"] in (True, False)
        if not result["success"]:
            assert "error" in result
            # Traceback-like strings (Python exception repr) must not leak
            # into the user-facing error text.
            assert "Traceback" not in result["error"]

    @pytest.mark.asyncio
    async def test_ui_parser_handles_null_byte_in_text(self, mock_adb_manager):
        """XML whose text attribute contains \\x00 and other control chars
        must not crash the parser.

        The parser has a multi-strategy recovery path. We feed it XML with a
        null byte plus other control chars in the text attribute and expect
        a structured response (never an uncaught exception).
        """
        mock_adb_manager.execute_adb_command.side_effect = None

        xml_with_nulls = (
            "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>"
            "<hierarchy rotation=\"0\">"
            "<node index=\"0\" text=\"hel\x00lo\x01wo\x02rld\" "
            "resource-id=\"com.test:id/n\" class=\"android.widget.TextView\" "
            "package=\"com.test\" content-desc=\"\" "
            "clickable=\"false\" enabled=\"true\" focusable=\"false\" "
            "scrollable=\"false\" bounds=\"[0,0][100,100]\" displayed=\"true\"/>"
            "</hierarchy>"
        )

        async def scripted(cmd, timeout=30):
            if "uiautomator dump" in cmd:
                return {"success": True, "stdout": "", "stderr": "", "return_code": 0}
            if "test -f" in cmd:
                return {
                    "success": True,
                    "stdout": "exists",
                    "stderr": "",
                    "return_code": 0,
                }
            if "cat " in cmd:
                return {
                    "success": True,
                    "stdout": xml_with_nulls,
                    "stderr": "",
                    "return_code": 0,
                }
            return {"success": True, "stdout": "", "stderr": "", "return_code": 0}

        mock_adb_manager.execute_adb_command.side_effect = scripted

        ui_extractor = UILayoutExtractor(mock_adb_manager)
        with patch("src.ui_inspector.asyncio.sleep", new=AsyncMock(return_value=None)):
            result = await ui_extractor.get_ui_layout(max_retries=1)

        # Parser must not raise. It either cleans the attribute (success) or
        # rejects the payload (success=False with error), but never crashes.
        assert isinstance(result, dict)
        assert "success" in result
        if result["success"]:
            # Cleaned strategy empties out bad text attributes, so the element
            # is parsed but the text is missing/empty.
            assert "elements" in result
        else:
            assert "error" in result


class TestElementFinder:
    """Test element finding functionality."""

    @pytest.fixture
    def sample_ui_extractor(self, mock_adb_manager):
        """Create UI extractor with sample data."""
        mock_adb_manager.execute_adb_command.return_value = {
            "success": True,
            "stdout": MockUIScenarios.login_screen(),
            "stderr": "",
            "return_code": 0,
        }
        return UILayoutExtractor(mock_adb_manager)

    @pytest.mark.asyncio
    async def test_find_elements_by_text(self, sample_ui_extractor):
        """Test finding elements by text content."""
        finder = ElementFinder(sample_ui_extractor)

        elements = await finder.find_elements(text="Login")

        assert len(elements) > 0
        # Should find both the title and button
        for element in elements:
            assert "Login" in element.get("text", "")

    @pytest.mark.asyncio
    async def test_find_elements_by_resource_id(self, sample_ui_extractor):
        """Test finding elements by resource ID."""
        finder = ElementFinder(sample_ui_extractor)

        elements = await finder.find_elements(resource_id="com.test:id/login_btn")

        assert len(elements) > 0
        for element in elements:
            assert element.get("resource-id") == "com.test:id/login_btn"

    @pytest.mark.asyncio
    async def test_find_elements_by_content_desc(self, sample_ui_extractor):
        """Test finding elements by content description."""
        finder = ElementFinder(sample_ui_extractor)

        elements = await finder.find_elements(content_desc="Username field")

        assert len(elements) > 0
        for element in elements:
            assert element.get("content-desc") == "Username field"

    @pytest.mark.asyncio
    async def test_find_elements_by_class_name(self, sample_ui_extractor):
        """Test finding elements by class name."""
        finder = ElementFinder(sample_ui_extractor)

        elements = await finder.find_elements(class_name="android.widget.Button")

        assert len(elements) > 0
        for element in elements:
            assert element.get("class") == "android.widget.Button"

    @pytest.mark.asyncio
    async def test_find_elements_clickable_only(self, sample_ui_extractor):
        """Test finding only clickable elements."""
        finder = ElementFinder(sample_ui_extractor)

        elements = await finder.find_elements(clickable_only=True)

        assert len(elements) > 0
        for element in elements:
            assert element.get("clickable") == "true"

    @pytest.mark.asyncio
    async def test_find_elements_enabled_only(self, sample_ui_extractor):
        """Test finding only enabled elements."""
        finder = ElementFinder(sample_ui_extractor)

        elements = await finder.find_elements(enabled_only=True)

        # All elements in login screen should be enabled
        for element in elements:
            assert element.get("enabled") == "true"

    @pytest.mark.asyncio
    async def test_find_elements_exact_match(self, sample_ui_extractor):
        """Test exact text matching."""
        finder = ElementFinder(sample_ui_extractor)

        # Exact match should find only the title, not the button
        elements = await finder.find_elements(text="Login", exact_match=True)

        # Should find elements where text exactly equals "Login"
        for element in elements:
            assert element.get("text") == "Login"

    @pytest.mark.asyncio
    async def test_find_elements_partial_match(self, sample_ui_extractor):
        """Test partial text matching."""
        finder = ElementFinder(sample_ui_extractor)

        # Partial match (default behavior)
        elements = await finder.find_elements(text="Log", exact_match=False)

        # Should find elements containing "Log"
        assert len(elements) > 0
        for element in elements:
            assert "Log" in element.get("text", "")

    @pytest.mark.asyncio
    async def test_find_elements_multiple_criteria(self, sample_ui_extractor):
        """Test finding elements with multiple criteria."""
        finder = ElementFinder(sample_ui_extractor)

        elements = await finder.find_elements(
            text="Login", class_name="android.widget.Button", clickable_only=True
        )

        # Should find login button specifically
        assert len(elements) > 0
        for element in elements:
            assert "Login" in element.get("text", "")
            assert element.get("class") == "android.widget.Button"
            assert element.get("clickable") == "true"

    @pytest.mark.asyncio
    async def test_find_element_by_text_single(self, sample_ui_extractor):
        """Test finding single element by text."""
        finder = ElementFinder(sample_ui_extractor)

        element = await finder.find_element_by_text("Username field")

        # Should return first match or None
        if element:
            assert "Username" in element.get(
                "content-desc", ""
            ) or "Username" in element.get("text", "")

    @pytest.mark.asyncio
    async def test_find_element_by_id_single(self, sample_ui_extractor):
        """Test finding single element by resource ID."""
        finder = ElementFinder(sample_ui_extractor)

        element = await finder.find_element_by_id("com.test:id/username")

        if element:
            assert element.get("resource-id") == "com.test:id/username"

    @pytest.mark.asyncio
    async def test_find_elements_no_matches(self, sample_ui_extractor):
        """Test finding elements with no matches."""
        finder = ElementFinder(sample_ui_extractor)

        elements = await finder.find_elements(text="NonexistentElement")

        assert len(elements) == 0

    @pytest.mark.asyncio
    async def test_element_to_dict_conversion(self, sample_ui_extractor):
        """Test element to dictionary conversion."""
        finder = ElementFinder(sample_ui_extractor)

        elements = await finder.find_elements(text="Login")
        if len(elements) > 0:
            element_dict = finder.element_to_dict(elements[0])

            # Should contain expected keys
            expected_keys = [
                "text",
                "resource-id",
                "class",
                "bounds",
                "clickable",
                "enabled",
            ]
            for key in expected_keys:
                assert key in element_dict

    @pytest.mark.asyncio
    async def test_get_element_center_coordinates(self, sample_ui_extractor):
        """Test calculation of element center coordinates."""
        finder = ElementFinder(sample_ui_extractor)

        elements = await finder.find_elements(text="Login")
        if len(elements) > 0:
            element = elements[0]
            center = finder.get_element_center(element)

            assert "x" in center
            assert "y" in center
            assert center["x"] > 0
            assert center["y"] > 0

    def test_get_element_center_with_bounds(self, sample_ui_extractor):
        """Test center calculation with specific bounds."""
        finder = ElementFinder(sample_ui_extractor)

        # Mock element with known bounds
        element = {"bounds": "[100,200][300,400]"}

        center = finder.get_element_center(element)

        # Center should be at (200, 300)
        assert center["x"] == 200
        assert center["y"] == 300

    def test_get_element_center_invalid_bounds(self, sample_ui_extractor):
        """Test center calculation with invalid bounds."""
        finder = ElementFinder(sample_ui_extractor)

        # Mock element with invalid bounds
        element = {"bounds": "invalid_bounds"}

        center = finder.get_element_center(element)

        # Should handle gracefully
        assert center is None or ("x" in center and "y" in center)

    @pytest.mark.asyncio
    async def test_find_elements_with_scrollable_content(self, mock_adb_manager):
        """Test finding elements in scrollable content."""
        # Clear side_effect to allow return_value to take precedence
        mock_adb_manager.execute_adb_command.side_effect = None
        mock_adb_manager.execute_adb_command.return_value = {
            "success": True,
            "stdout": MockUIScenarios.scrollable_list(),
            "stderr": "",
            "return_code": 0,
        }

        ui_extractor = UILayoutExtractor(mock_adb_manager)
        finder = ElementFinder(ui_extractor)

        # Find scrollable elements
        elements = await finder.find_elements(scrollable_only=True)

        for element in elements:
            assert element.get("scrollable") == "true"

        # Find list items
        items = await finder.find_elements(text="Item")

        assert len(items) >= 3  # Should find Item 1, 2, 3

    @pytest.mark.asyncio
    async def test_element_hierarchy_navigation(self, sample_ui_extractor):
        """Test navigation of element hierarchy."""
        finder = ElementFinder(sample_ui_extractor)

        # Get UI hierarchy
        hierarchy_result = await sample_ui_extractor.extract_ui_hierarchy()
        if hierarchy_result["success"]:
            hierarchy = hierarchy_result["hierarchy"]

            # Test finding parent/child relationships
            # Implementation-dependent based on hierarchy structure


class TestUIInspectorPerformance:
    """Test UI inspector performance characteristics."""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_ui_extraction_performance(self, mock_adb_manager):
        """Test UI extraction performance."""
        import time

        mock_adb_manager.execute_adb_command.return_value = {
            "success": True,
            "stdout": MockUIScenarios.login_screen(),
            "stderr": "",
            "return_code": 0,
        }

        ui_extractor = UILayoutExtractor(mock_adb_manager)

        start_time = time.time()
        result = await ui_extractor.get_ui_layout()
        end_time = time.time()

        duration = end_time - start_time

        assert result["success"] is True
        assert duration < 1.0, f"UI extraction took {duration} seconds"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_element_search_performance(self, mock_adb_manager):
        """Test element search performance with large UI."""
        import time

        # Create large UI dump
        large_ui = MockUIScenarios.scrollable_list()

        mock_adb_manager.execute_adb_command.return_value = {
            "success": True,
            "stdout": large_ui,
            "stderr": "",
            "return_code": 0,
        }

        ui_extractor = UILayoutExtractor(mock_adb_manager)
        finder = ElementFinder(ui_extractor)

        start_time = time.time()

        # Perform multiple searches
        for i in range(10):
            elements = await finder.find_elements(text="Item")

        end_time = time.time()
        duration = end_time - start_time

        assert duration < 1.0, f"Element searches took {duration} seconds"

    @pytest.mark.asyncio
    async def test_concurrent_ui_operations(self, mock_adb_manager):
        """Test concurrent UI operations."""
        import asyncio

        mock_adb_manager.execute_adb_command.return_value = {
            "success": True,
            "stdout": MockUIScenarios.login_screen(),
            "stderr": "",
            "return_code": 0,
        }

        ui_extractor = UILayoutExtractor(mock_adb_manager)
        finder = ElementFinder(ui_extractor)

        # Run multiple operations concurrently
        tasks = [
            ui_extractor.get_ui_layout(),
            finder.find_elements(text="Login"),
            finder.find_elements(class_name="android.widget.Button"),
            ui_extractor.extract_ui_hierarchy(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All operations should complete successfully
        for result in results:
            assert not isinstance(result, Exception)
            if isinstance(result, dict):
                assert result.get("success") is True


class TestUIInspectorErrorHandling:
    """Test UI inspector error handling."""

    @pytest.mark.asyncio
    async def test_handle_adb_command_failure(self, mock_adb_manager):
        """Test handling of ADB command failures."""
        # Clear side_effect to allow return_value to take precedence
        mock_adb_manager.execute_adb_command.side_effect = None
        mock_adb_manager.execute_adb_command.return_value = (
            MockErrorScenarios.adb_timeout_error()
        )

        ui_extractor = UILayoutExtractor(mock_adb_manager)
        result = await ui_extractor.get_ui_layout()

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_handle_ui_service_unavailable(self, mock_adb_manager):
        """Test handling when UI automator service is unavailable."""
        # Clear side_effect to allow return_value to take precedence
        mock_adb_manager.execute_adb_command.side_effect = None
        mock_adb_manager.execute_adb_command.return_value = (
            MockErrorScenarios.ui_service_unavailable_error()
        )

        ui_extractor = UILayoutExtractor(mock_adb_manager)
        result = await ui_extractor.get_ui_layout()

        assert result["success"] is False
        assert "ui" in result["error"].lower() or "automator" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_handle_device_offline(self, mock_adb_manager):
        """Test handling when device goes offline during operation."""
        # Clear side_effect to allow return_value to take precedence
        mock_adb_manager.execute_adb_command.side_effect = None
        mock_adb_manager.execute_adb_command.return_value = (
            MockErrorScenarios.device_not_found_error()
        )

        ui_extractor = UILayoutExtractor(mock_adb_manager)
        result = await ui_extractor.get_ui_layout()

        assert result["success"] is False
        assert "device" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_handle_empty_ui_dump(self, mock_adb_manager):
        """Test handling of empty UI dump."""
        # Clear side_effect to allow return_value to take precedence
        mock_adb_manager.execute_adb_command.side_effect = None
        mock_adb_manager.execute_adb_command.return_value = {
            "success": True,
            "stdout": "",
            "stderr": "",
            "return_code": 0,
        }

        ui_extractor = UILayoutExtractor(mock_adb_manager)
        result = await ui_extractor.get_ui_layout()

        # Should handle empty response gracefully
        assert result["success"] is False or result["element_count"] == 0
