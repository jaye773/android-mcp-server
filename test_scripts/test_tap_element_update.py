#!/usr/bin/env python3
"""Test script to verify tap_element improvements."""

import asyncio
import sys

from src.adb_manager import ADBManager
from src.screen_interactor import ScreenInteractor
from src.ui_inspector import UILayoutExtractor


async def test_tap_element():
    """Test the updated tap_element function."""
    try:
        # Initialize components
        adb_manager = ADBManager()
        device_result = await adb_manager.auto_select_device()
        if not device_result["success"]:
            print(f"Failed to select device: {device_result}")
            return

        print(f"Selected device: {device_result['selected']['id']}")

        ui_inspector = UILayoutExtractor(adb_manager)
        screen_interactor = ScreenInteractor(adb_manager, ui_inspector)

        # Test 1: Try to tap "New task" with defaults (should work now)
        print("\nTest 1: Tapping 'New task' with new defaults (clickable_only=False)...")
        result = await screen_interactor.tap_element(
            text="New task",
            clickable_only=False,
            enabled_only=False
        )
        print(f"Result: {result}")

        if not result["success"]:
            print("\nTest 1.5: Searching for any element with 'New' text...")
            # Try partial match
            from src.ui_inspector import ElementFinder
            finder = ElementFinder(ui_inspector)
            elements = await finder.find_elements(
                text="New",
                clickable_only=False,
                enabled_only=False
            )
            print(f"Found {len(elements)} elements with 'New' text")
            for i, elem in enumerate(elements):
                print(f"  {i}: {elem.get('text')} - clickable: {elem.get('clickable')}")

        # Test 2: Try with old defaults (should fail)
        print("\nTest 2: Tapping 'New task' with old defaults (clickable_only=True)...")
        result2 = await screen_interactor.tap_element(
            text="New task",
            clickable_only=True,
            enabled_only=True
        )
        print(f"Result: {result2}")

        # Test 3: Try tapping by resource ID
        print("\nTest 3: Tapping newTaskButton by resource ID...")
        result3 = await screen_interactor.tap_element(
            resource_id="com.example.androidmcptestapp:id/newTaskButton",
            clickable_only=False,
            enabled_only=False
        )
        print(f"Result: {result3}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_tap_element())