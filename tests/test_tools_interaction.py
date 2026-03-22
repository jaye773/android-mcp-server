"""Dedicated unit tests for src/tools/interaction.py.

Covers all 6 tool functions:
  - tap_screen: happy path, missing component, exception
  - tap_element: happy path, validation failure, no validator (warning path), missing component, exception
  - swipe_screen: happy path, missing component, exception
  - swipe_direction: happy path, missing component, exception
  - input_text: happy path, validation failure, missing component, exception
  - press_key: happy path, validation failure, missing component, exception
  - register_interaction_tools wiring
"""

import pytest
from unittest.mock import MagicMock

from src.tools.interaction import (
    input_text,
    press_key,
    register_interaction_tools,
    swipe_direction,
    swipe_screen,
    tap_element,
    tap_screen,
)
from src.tool_models import (
    KeyPressParams,
    SwipeDirectionParams,
    SwipeParams,
    TapCoordinatesParams,
    TapElementParams,
    TextInputParams,
)
from src.registry import ComponentRegistry
from src.validation import ValidationResult


@pytest.fixture(autouse=True)
def _clean_registry():
    ComponentRegistry.reset()
    yield
    ComponentRegistry.reset()


# ---------------------------------------------------------------------------
# tap_screen
# ---------------------------------------------------------------------------


class TestTapScreen:
    @pytest.mark.asyncio
    async def test_happy_path(self, mock_screen_interactor):
        ComponentRegistry.instance().register("screen_interactor", mock_screen_interactor)

        params = TapCoordinatesParams(x=100, y=200)
        result = await tap_screen(params)

        assert result["success"] is True
        mock_screen_interactor.tap_coordinates.assert_awaited_once_with(100, 200)

    @pytest.mark.asyncio
    async def test_missing_component(self):
        params = TapCoordinatesParams(x=100, y=200)
        result = await tap_screen(params)

        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_exception(self, mock_screen_interactor):
        ComponentRegistry.instance().register("screen_interactor", mock_screen_interactor)
        mock_screen_interactor.tap_coordinates.side_effect = RuntimeError("tap fail")

        params = TapCoordinatesParams(x=100, y=200)
        result = await tap_screen(params)

        assert result["success"] is False
        assert "tap fail" in result["error"]


# ---------------------------------------------------------------------------
# tap_element
# ---------------------------------------------------------------------------


class TestTapElement:
    @pytest.mark.asyncio
    async def test_happy_path(self, mock_screen_interactor, mock_validator):
        reg = ComponentRegistry.instance()
        reg.register("screen_interactor", mock_screen_interactor)
        reg.register("validator", mock_validator)

        params = TapElementParams(text="Login")
        result = await tap_element(params)

        assert result["success"] is True
        mock_screen_interactor.tap_element.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_validation_failure(self, mock_screen_interactor, mock_validator):
        reg = ComponentRegistry.instance()
        reg.register("screen_interactor", mock_screen_interactor)
        reg.register("validator", mock_validator)

        # Make validator reject the input
        fail_result = ValidationResult(False, None, ["injection detected"], [])
        mock_validator.validate_element_search.return_value = fail_result

        params = TapElementParams(text="bad; rm -rf")
        result = await tap_element(params)

        assert result["success"] is False
        assert "Validation failed" in result["error"]
        # Underlying interactor should NOT be called
        mock_screen_interactor.tap_element.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_validator_still_works(self, mock_screen_interactor):
        """When validator is not registered, tap_element should still work (with warning)."""
        ComponentRegistry.instance().register("screen_interactor", mock_screen_interactor)

        params = TapElementParams(text="Login")
        result = await tap_element(params)

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_missing_screen_interactor(self):
        params = TapElementParams(text="Login")
        result = await tap_element(params)

        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_exception(self, mock_screen_interactor, mock_validator):
        reg = ComponentRegistry.instance()
        reg.register("screen_interactor", mock_screen_interactor)
        reg.register("validator", mock_validator)
        mock_screen_interactor.tap_element.side_effect = RuntimeError("element tap fail")

        params = TapElementParams(text="Login")
        result = await tap_element(params)

        assert result["success"] is False
        assert "element tap fail" in result["error"]


# ---------------------------------------------------------------------------
# swipe_screen
# ---------------------------------------------------------------------------


class TestSwipeScreen:
    @pytest.mark.asyncio
    async def test_happy_path(self, mock_gesture_controller):
        ComponentRegistry.instance().register("gesture_controller", mock_gesture_controller)

        params = SwipeParams(start_x=100, start_y=200, end_x=300, end_y=400, duration_ms=300)
        result = await swipe_screen(params)

        assert result["success"] is True
        mock_gesture_controller.swipe_coordinates.assert_awaited_once_with(100, 200, 300, 400, 300)

    @pytest.mark.asyncio
    async def test_missing_component(self):
        params = SwipeParams(start_x=100, start_y=200, end_x=300, end_y=400)
        result = await swipe_screen(params)

        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_exception(self, mock_gesture_controller):
        ComponentRegistry.instance().register("gesture_controller", mock_gesture_controller)
        mock_gesture_controller.swipe_coordinates.side_effect = RuntimeError("swipe fail")

        params = SwipeParams(start_x=100, start_y=200, end_x=300, end_y=400)
        result = await swipe_screen(params)

        assert result["success"] is False
        assert "swipe fail" in result["error"]


# ---------------------------------------------------------------------------
# swipe_direction
# ---------------------------------------------------------------------------


class TestSwipeDirection:
    @pytest.mark.asyncio
    async def test_happy_path(self, mock_gesture_controller):
        ComponentRegistry.instance().register("gesture_controller", mock_gesture_controller)

        params = SwipeDirectionParams(direction="up", distance=500, duration_ms=300)
        result = await swipe_direction(params)

        assert result["success"] is True
        mock_gesture_controller.swipe_direction.assert_awaited_once_with(
            direction="up", distance=500, duration_ms=300
        )

    @pytest.mark.asyncio
    async def test_missing_component(self):
        params = SwipeDirectionParams(direction="down")
        result = await swipe_direction(params)

        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_exception(self, mock_gesture_controller):
        ComponentRegistry.instance().register("gesture_controller", mock_gesture_controller)
        mock_gesture_controller.swipe_direction.side_effect = RuntimeError("direction fail")

        params = SwipeDirectionParams(direction="left")
        result = await swipe_direction(params)

        assert result["success"] is False
        assert "direction fail" in result["error"]


# ---------------------------------------------------------------------------
# input_text
# ---------------------------------------------------------------------------


class TestInputText:
    @pytest.mark.asyncio
    async def test_happy_path(self, mock_text_controller, mock_validator):
        reg = ComponentRegistry.instance()
        reg.register("text_controller", mock_text_controller)
        reg.register("validator", mock_validator)

        params = TextInputParams(text="hello world")
        result = await input_text(params)

        assert result["success"] is True
        mock_text_controller.input_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_validation_failure(self, mock_text_controller, mock_validator):
        reg = ComponentRegistry.instance()
        reg.register("text_controller", mock_text_controller)
        reg.register("validator", mock_validator)

        fail_result = ValidationResult(False, None, ["shell injection detected"], [])
        mock_validator.validate_text_input.return_value = fail_result

        params = TextInputParams(text="; rm -rf /")
        result = await input_text(params)

        assert result["success"] is False
        assert "Validation failed" in result["error"]
        mock_text_controller.input_text.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_validator_skips_validation(self, mock_text_controller):
        """Without validator, input_text proceeds without security check."""
        ComponentRegistry.instance().register("text_controller", mock_text_controller)

        params = TextInputParams(text="hello")
        result = await input_text(params)

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_missing_text_controller(self):
        params = TextInputParams(text="hello")
        result = await input_text(params)

        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_exception(self, mock_text_controller, mock_validator):
        reg = ComponentRegistry.instance()
        reg.register("text_controller", mock_text_controller)
        reg.register("validator", mock_validator)
        mock_text_controller.input_text.side_effect = RuntimeError("input fail")

        params = TextInputParams(text="hello")
        result = await input_text(params)

        assert result["success"] is False
        assert "input fail" in result["error"]


# ---------------------------------------------------------------------------
# press_key
# ---------------------------------------------------------------------------


class TestPressKey:
    @pytest.mark.asyncio
    async def test_happy_path(self, mock_text_controller, mock_validator):
        reg = ComponentRegistry.instance()
        reg.register("text_controller", mock_text_controller)
        reg.register("validator", mock_validator)

        params = KeyPressParams(keycode="ENTER")
        result = await press_key(params)

        assert result["success"] is True
        mock_text_controller.press_key.assert_awaited_once_with("ENTER")

    @pytest.mark.asyncio
    async def test_validation_failure(self, mock_text_controller, mock_validator):
        reg = ComponentRegistry.instance()
        reg.register("text_controller", mock_text_controller)
        reg.register("validator", mock_validator)

        fail_result = ValidationResult(False, None, ["unknown keycode"], [])
        mock_validator.validate_key_input.return_value = fail_result

        params = KeyPressParams(keycode="EVIL_KEY")
        result = await press_key(params)

        assert result["success"] is False
        assert "Validation failed" in result["error"]
        mock_text_controller.press_key.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_validator_skips_validation(self, mock_text_controller):
        ComponentRegistry.instance().register("text_controller", mock_text_controller)

        params = KeyPressParams(keycode="BACK")
        result = await press_key(params)

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_missing_text_controller(self):
        params = KeyPressParams(keycode="ENTER")
        result = await press_key(params)

        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_exception(self, mock_text_controller, mock_validator):
        reg = ComponentRegistry.instance()
        reg.register("text_controller", mock_text_controller)
        reg.register("validator", mock_validator)
        mock_text_controller.press_key.side_effect = RuntimeError("key fail")

        params = KeyPressParams(keycode="ENTER")
        result = await press_key(params)

        assert result["success"] is False
        assert "key fail" in result["error"]


# ---------------------------------------------------------------------------
# register_interaction_tools
# ---------------------------------------------------------------------------


class TestRegisterInteractionTools:
    def test_registers_six_tools(self):
        mcp = MagicMock()
        mcp.tool.return_value = lambda fn: fn

        register_interaction_tools(mcp)

        assert mcp.tool.call_count == 6
