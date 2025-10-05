from unittest.mock import AsyncMock

import pytest

from src.screen_interactor import (
    GestureController,
    ScreenInteractor,
    TextInputController,
)


class DummyADB:
    def __init__(self):
        self.selected_device = "emulator-5554"
        self.calls = []

    async def execute_adb_command(
        self, command, timeout=30, capture_output=True, check_device=True
    ):
        self.calls.append(command)
        return {"success": True, "stdout": "", "stderr": "", "returncode": 0}

    async def get_screen_size(self):
        return {"success": True, "width": 1080, "height": 1920}


class DummyUI:
    pass


@pytest.mark.asyncio
async def test_tap_and_long_press_and_swipe_coordinates():
    adb = DummyADB()
    ui = DummyUI()
    interactor = ScreenInteractor(adb, ui)
    gesture = GestureController(adb)

    tap_res = await interactor.tap_coordinates(10, 20)
    assert tap_res["success"] is True
    assert tap_res["action"] == "tap"

    lp_res = await interactor.long_press_coordinates(10, 20, duration_ms=200)
    assert lp_res["success"] is True
    assert lp_res["action"] == "long_press"

    swipe_res = await gesture.swipe_coordinates(0, 0, 100, 100, duration_ms=300)
    assert swipe_res["success"] is True
    assert swipe_res["action"] == "swipe"


@pytest.mark.asyncio
async def test_swipe_direction_and_press_key_and_clear():
    adb = DummyADB()
    ui = DummyUI()
    interactor = ScreenInteractor(adb, ui)
    gesture = GestureController(adb)

    # swipe_direction uses get_screen_size -> provided by DummyADB
    dir_res = await gesture.swipe_direction(
        "up", distance=300, start_point=(540, 960), duration_ms=200
    )
    assert dir_res["success"] is True
    assert dir_res["direction"] == "up"

    # press_key mapping via TextInputController
    tic = TextInputController(adb)
    key_res = await tic.press_key("back")
    assert key_res["success"] is True
    assert key_res["keycode"] == "KEYCODE_BACK"

    # clear_text_field uses adb + DEL press
    tic.press_key = AsyncMock(return_value={"success": True})
    clr_res = await tic.clear_text_field()
    assert clr_res["success"] is True
