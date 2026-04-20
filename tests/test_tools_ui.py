"""Dedicated unit tests for src/tools/ui.py.

Covers:
  - _parse_bounds_to_coordinates: valid, invalid, zero-area
  - _transform_element_to_screen_format: full element, missing bounds, exception
  - _is_meaningful_element: interactive, has-content, neither, zero-area
  - get_ui_layout: happy path, dict elements, UIElement objects, missing component, exception
  - list_screen_elements: happy path, no device selected (auto-select), no devices connected,
      Chrome fallback on timeout, non-Chrome timeout, missing components, exception
  - find_elements: happy path, validation failure, search timeout, missing components, exception
  - register_ui_tools wiring
"""

import asyncio

import pytest
from unittest.mock import MagicMock

from src.tools.ui import (
    _is_meaningful_element,
    _parse_bounds_to_coordinates,
    _transform_element_to_screen_format,
    find_elements,
    get_ui_layout,
    list_screen_elements,
    register_ui_tools,
)
from src.tool_models import ElementSearchParams, UILayoutParams
from src.registry import ComponentRegistry
from src.validation import ValidationResult


@pytest.fixture(autouse=True)
def _clean_registry():
    ComponentRegistry.reset()
    yield
    ComponentRegistry.reset()


# ---------------------------------------------------------------------------
# Helper: _parse_bounds_to_coordinates
# ---------------------------------------------------------------------------


class TestParseBoundsToCoordinates:
    def test_valid_bounds(self):
        result = _parse_bounds_to_coordinates("[100,200][300,400]")
        assert result == {"x": 100, "y": 200, "width": 200, "height": 200}

    def test_invalid_bounds_returns_none(self):
        result = _parse_bounds_to_coordinates("not-bounds")
        assert result is None

    def test_zero_area_returns_none(self):
        result = _parse_bounds_to_coordinates("[100,200][100,200]")
        assert result is None

    def test_swapped_coords_auto_corrects(self):
        """parse_bounds auto-corrects swapped coords, so width/height are still positive."""
        result = _parse_bounds_to_coordinates("[300,200][100,400]")
        # Auto-corrected: left=100, top=200, right=300, bottom=400
        assert result == {"x": 100, "y": 200, "width": 200, "height": 200}


# ---------------------------------------------------------------------------
# Helper: _transform_element_to_screen_format
# ---------------------------------------------------------------------------


class TestTransformElement:
    def test_full_element(self):
        element = {
            "class": "android.widget.Button",
            "text": "Login",
            "content-desc": "Login button",
            "resource-id": "com.app:id/login",
            "bounds": "[100,200][300,400]",
            "clickable": "true",
            "enabled": "true",
            "focusable": "true",
            "scrollable": "false",
        }
        result = _transform_element_to_screen_format(element)

        assert result is not None
        assert result["type"] == "android.widget.Button"
        assert result["text"] == "Login"
        assert result["label"] == "Login button"
        assert result["identifier"] == "com.app:id/login"
        assert result["coordinates"]["x"] == 100
        assert result["clickable"] is True
        assert result["enabled"] is True
        assert result["focusable"] is True
        assert "scrollable" not in result  # "false" string -> not added

    def test_missing_bounds_returns_none(self):
        element = {"class": "android.widget.Button", "text": "X"}
        result = _transform_element_to_screen_format(element)
        # Default bounds "[0,0][0,0]" -> zero area -> None
        assert result is None

    def test_invalid_bounds_returns_none(self):
        element = {"bounds": "garbage", "text": "X"}
        result = _transform_element_to_screen_format(element)
        assert result is None


# ---------------------------------------------------------------------------
# Helper: _is_meaningful_element
# ---------------------------------------------------------------------------


class TestIsMeaningfulElement:
    def test_has_text(self):
        element = {"text": "Hello", "coordinates": {"width": 100, "height": 50}}
        assert _is_meaningful_element(element) is True

    def test_has_label(self):
        element = {"label": "Desc", "coordinates": {"width": 100, "height": 50}}
        assert _is_meaningful_element(element) is True

    def test_has_identifier(self):
        element = {"identifier": "com.app:id/btn", "coordinates": {"width": 100, "height": 50}}
        assert _is_meaningful_element(element) is True

    def test_is_clickable(self):
        element = {"clickable": True, "coordinates": {"width": 100, "height": 50}}
        assert _is_meaningful_element(element) is True

    def test_is_scrollable(self):
        element = {"scrollable": True, "coordinates": {"width": 100, "height": 50}}
        assert _is_meaningful_element(element) is True

    def test_empty_element(self):
        element = {"coordinates": {"width": 100, "height": 50}}
        assert _is_meaningful_element(element) is False

    def test_zero_width(self):
        element = {"text": "Hello", "coordinates": {"width": 0, "height": 50}}
        assert _is_meaningful_element(element) is False

    def test_zero_height(self):
        element = {"text": "Hello", "coordinates": {"width": 100, "height": 0}}
        assert _is_meaningful_element(element) is False


# ---------------------------------------------------------------------------
# get_ui_layout
# ---------------------------------------------------------------------------


class TestGetUiLayout:
    @pytest.mark.asyncio
    async def test_happy_path(self, mock_ui_inspector, mock_adb_manager):
        ComponentRegistry.instance().register("ui_inspector", mock_ui_inspector)


        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
        params = UILayoutParams(compressed=True, include_invisible=False)
        result = await get_ui_layout(params)

        assert result["success"] is True
        assert "elements" in result
        mock_ui_inspector.get_ui_layout.assert_awaited_once_with(
            compressed=True, include_invisible=False
        , device_id="emulator-5554")

    @pytest.mark.asyncio
    async def test_dict_elements_passthrough(self, mock_ui_inspector, mock_adb_manager):
        """Dict elements are kept as-is."""
        ComponentRegistry.instance().register("ui_inspector", mock_ui_inspector)
        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
        mock_ui_inspector.get_ui_layout.return_value = {
            "success": True,
            "elements": [{"class": "Button", "text": "OK"}],
        }

        params = UILayoutParams()
        result = await get_ui_layout(params)

        assert result["success"] is True
        assert result["elements"][0]["text"] == "OK"

    @pytest.mark.asyncio
    async def test_failed_layout(self, mock_ui_inspector, mock_adb_manager):
        """If inspector returns success=False, propagate as-is."""
        ComponentRegistry.instance().register("ui_inspector", mock_ui_inspector)
        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
        mock_ui_inspector.get_ui_layout.return_value = {
            "success": False,
            "error": "dump failed",
        }

        params = UILayoutParams()
        result = await get_ui_layout(params)

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_missing_component(self):
        params = UILayoutParams()
        result = await get_ui_layout(params)

        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_exception(self, mock_ui_inspector, mock_adb_manager):
        ComponentRegistry.instance().register("ui_inspector", mock_ui_inspector)

        ComponentRegistry.instance().register("adb_manager", mock_adb_manager)
        mock_ui_inspector.get_ui_layout.side_effect = RuntimeError("dump crash")

        params = UILayoutParams()
        result = await get_ui_layout(params)

        assert result["success"] is False
        assert "dump crash" in result["error"]


# ---------------------------------------------------------------------------
# list_screen_elements
# ---------------------------------------------------------------------------


class TestListScreenElements:
    @pytest.mark.asyncio
    async def test_happy_path(self, mock_ui_inspector, mock_adb_manager):
        reg = ComponentRegistry.instance()
        reg.register("ui_inspector", mock_ui_inspector)
        reg.register("adb_manager", mock_adb_manager)
        mock_adb_manager.get_foreground_app.return_value = {
            "success": True,
            "package": "com.example.app",
        }
        mock_ui_inspector.get_ui_layout.return_value = {
            "success": True,
            "elements": [
                {
                    "class": "android.widget.Button",
                    "text": "OK",
                    "content-desc": "",
                    "resource-id": "com.app:id/ok",
                    "bounds": "[100,200][300,400]",
                    "clickable": "true",
                    "enabled": "true",
                    "focusable": "false",
                    "scrollable": "false",
                }
            ],
        }

        result = await list_screen_elements()

        assert result["success"] is True
        assert result["count"] >= 1
        assert result["elements"][0]["text"] == "OK"

    @pytest.mark.asyncio
    async def test_no_device_selected_auto_select(self, mock_ui_inspector, mock_adb_manager):
        """When no device is selected, auto-select should be attempted."""
        reg = ComponentRegistry.instance()
        reg.register("ui_inspector", mock_ui_inspector)
        reg.register("adb_manager", mock_adb_manager)
        mock_adb_manager.selected_device = None
        mock_adb_manager.list_devices.return_value = [{"id": "emu-5554"}]
        mock_adb_manager.auto_select_device.return_value = {"success": True}
        mock_adb_manager.get_foreground_app.return_value = {
            "success": True,
            "package": "com.example.app",
        }
        mock_ui_inspector.get_ui_layout.return_value = {
            "success": True,
            "elements": [],
        }

        result = await list_screen_elements()

        assert result["success"] is True
        mock_adb_manager.auto_select_device.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_devices_connected(self, mock_ui_inspector, mock_adb_manager):
        reg = ComponentRegistry.instance()
        reg.register("ui_inspector", mock_ui_inspector)
        reg.register("adb_manager", mock_adb_manager)
        mock_adb_manager.selected_device = None
        mock_adb_manager.list_devices.return_value = []

        result = await list_screen_elements()

        assert result["success"] is False
        assert "No Android devices connected" in result["error"]

    @pytest.mark.asyncio
    async def test_missing_components(self):
        result = await list_screen_elements()

        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_exception(self, mock_ui_inspector, mock_adb_manager):
        reg = ComponentRegistry.instance()
        reg.register("ui_inspector", mock_ui_inspector)
        reg.register("adb_manager", mock_adb_manager)
        mock_adb_manager.get_foreground_app.side_effect = RuntimeError("fg crash")

        result = await list_screen_elements()

        assert result["success"] is False
        assert "fg crash" in result["error"]

    @pytest.mark.asyncio
    async def test_chrome_timeout_returns_failure(
        self, mock_ui_inspector, mock_adb_manager
    ):
        """When Chrome is foreground and UI dump times out, return clean failure
        with a take_screenshot hint instead of fabricating elements."""
        reg = ComponentRegistry.instance()
        reg.register("ui_inspector", mock_ui_inspector)
        reg.register("adb_manager", mock_adb_manager)

        mock_adb_manager.get_foreground_app.return_value = {
            "success": True,
            "package": "com.android.chrome",
        }
        mock_ui_inspector.get_ui_layout.side_effect = asyncio.TimeoutError()

        result = await list_screen_elements()

        assert result["success"] is False
        assert result.get("hint") == "take_screenshot"
        # Fabrication must not leak back to caller
        assert "elements" not in result
        assert "mode" not in result
        assert "count" not in result
        # Screen size must NOT be consulted for synthesis
        mock_adb_manager.get_screen_size.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_chrome_timeout_returns_failure(
        self, mock_ui_inspector, mock_adb_manager
    ):
        """Non-Chrome timeout still returns a failure with the existing
        recovery-suggestions shape (no fabrication)."""
        reg = ComponentRegistry.instance()
        reg.register("ui_inspector", mock_ui_inspector)
        reg.register("adb_manager", mock_adb_manager)

        mock_adb_manager.get_foreground_app.return_value = {
            "success": True,
            "package": "com.example.app",
        }
        mock_ui_inspector.get_ui_layout.side_effect = asyncio.TimeoutError()

        result = await list_screen_elements()

        assert result["success"] is False
        assert "Timed out" in result["error"]
        assert result["elements"] == []
        assert "hint" not in result


# ---------------------------------------------------------------------------
# find_elements
# ---------------------------------------------------------------------------


class TestFindElements:
    @pytest.mark.asyncio
    async def test_happy_path(self, mock_ui_inspector, mock_validator, mock_adb_manager):
        reg = ComponentRegistry.instance()
        reg.register("ui_inspector", mock_ui_inspector)
        reg.register("adb_manager", mock_adb_manager)
        reg.register("validator", mock_validator)

        params = ElementSearchParams(text="Login")
        result = await find_elements(params)

        assert result["success"] is True
        assert "elements" in result
        assert "execution_time" in result

    @pytest.mark.asyncio
    async def test_validation_failure(self, mock_ui_inspector, mock_validator, mock_adb_manager):
        reg = ComponentRegistry.instance()
        reg.register("ui_inspector", mock_ui_inspector)
        reg.register("adb_manager", mock_adb_manager)
        reg.register("validator", mock_validator)

        fail_result = ValidationResult(False, None, ["injection detected"], [])
        mock_validator.validate_element_search.return_value = fail_result

        params = ElementSearchParams(text="bad; rm -rf /")
        result = await find_elements(params)

        assert result["success"] is False
        assert "Validation failed" in result["error"]

    @pytest.mark.asyncio
    async def test_missing_components(self):
        """Both ui_inspector and validator must be present."""
        params = ElementSearchParams(text="Login")
        result = await find_elements(params)

        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_exception(self, mock_ui_inspector, mock_validator, mock_adb_manager):
        reg = ComponentRegistry.instance()
        reg.register("ui_inspector", mock_ui_inspector)
        reg.register("adb_manager", mock_adb_manager)
        reg.register("validator", mock_validator)

        # Make the validator pass but have exception elsewhere
        mock_validator.validate_element_search.side_effect = RuntimeError("validator crash")

        params = ElementSearchParams(text="Login")
        result = await find_elements(params)

        assert result["success"] is False
        assert "validator crash" in result["error"]


# ---------------------------------------------------------------------------
# register_ui_tools
# ---------------------------------------------------------------------------


class TestRegisterUiTools:
    def test_registers_three_tools(self):
        mcp = MagicMock()
        mcp.tool.return_value = lambda fn: fn

        register_ui_tools(mcp)

        assert mcp.tool.call_count == 3


# ---------------------------------------------------------------------------
# T10: Per-request device pinning — midflight-switch regression for UI layout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_device_switch_midflight_ui_layout():
    """get_ui_layout is a multi-step flow (dump → test -f → cat) — every
    step must target the device id that was snapshotted at entry even if
    ``selected_device`` is mutated between steps.
    """
    from src.ui_retriever import UILayoutExtractor

    class _DumpADB:
        def __init__(self):
            self.selected_device = "device-A"
            self.calls: list[tuple[str, str]] = []
            # Mutate selected_device after the first adb call to simulate
            # a concurrent select_device() while a dump is in flight.
            self._mutated = False

        def default_device_id(self) -> str:
            if not self.selected_device:
                raise RuntimeError("no device selected")
            return self.selected_device

        async def execute_adb_command(
            self,
            command: str,
            *,
            device_id,
            timeout: int = 30,
            capture_output: bool = True,
            check_device: bool = True,
        ):
            if "uiautomator dump" in command:
                kind = "dump"
            elif "test -f" in command:
                kind = "test_f"
            elif "cat /sdcard" in command:
                kind = "cat"
            else:
                kind = "other"
            self.calls.append((kind, device_id))
            # After the dump stage, simulate a client mutating selected_device.
            if kind == "dump" and not self._mutated:
                self._mutated = True
                self.selected_device = "device-B"
            if kind == "cat":
                return {
                    "success": True,
                    "stdout": (
                        "<?xml version='1.0'?>"
                        "<hierarchy rotation=\"0\">"
                        "<node class=\"android.widget.LinearLayout\" "
                        "bounds=\"[0,0][100,100]\" />"
                        "</hierarchy>"
                    ),
                    "stderr": "",
                    "returncode": 0,
                }
            if kind == "test_f":
                return {
                    "success": True,
                    "stdout": "exists",
                    "stderr": "",
                    "returncode": 0,
                }
            return {"success": True, "stdout": "", "stderr": "", "returncode": 0}

    adb = _DumpADB()
    extractor = UILayoutExtractor(adb_manager=adb)
    pinned = adb.default_device_id()

    result = await extractor.get_ui_layout(
        retry_on_failure=False, device_id=pinned
    )

    assert result["success"] is True, result
    # Must see at least dump and cat calls, all pinned to device-A even
    # though selected_device was mutated mid-flight.
    kinds = [k for k, _ in adb.calls]
    assert "dump" in kinds and "cat" in kinds, kinds
    assert all(dev == "device-A" for _, dev in adb.calls), (
        f"expected all UI-dump subcalls pinned to device-A, got {adb.calls!r}"
    )
    assert adb.selected_device == "device-B"
