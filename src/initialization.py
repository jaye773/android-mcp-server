"""Component initialization for MCP server."""

import logging
from typing import Any, Dict

from .adb_manager import ADBManager
from .log_monitor import LogMonitor
from .media_capture import MediaCapture, VideoRecorder
from .screen_interactor import GestureController, ScreenInteractor, TextInputController
from .ui_inspector import UILayoutExtractor
from .validation import ComprehensiveValidator, SecurityLevel

logger = logging.getLogger(__name__)


async def initialize_components() -> Dict[str, Any]:
    """Initialize all server components.

    Returns:
        Dictionary containing all initialized components and validator
    """
    try:
        # Initialize ADB manager
        adb_manager = ADBManager()

        # Auto-select first device
        device_result = await adb_manager.auto_select_device()
        if device_result["success"]:
            logger.info(f"Auto-selected device: {device_result['selected']['id']}")
        else:
            logger.warning(f"No devices available: {device_result.get('error')}")

        # Initialize other components
        ui_inspector = UILayoutExtractor(adb_manager)
        screen_interactor = ScreenInteractor(adb_manager, ui_inspector)
        gesture_controller = GestureController(adb_manager)
        text_controller = TextInputController(adb_manager)
        media_capture = MediaCapture(adb_manager)
        video_recorder = VideoRecorder(adb_manager)
        log_monitor = LogMonitor(adb_manager)

        # Initialize validator with strict security by default
        validator = ComprehensiveValidator(SecurityLevel.STRICT)

        logger.info("All components initialized successfully")

        return {
            "adb_manager": adb_manager,
            "ui_inspector": ui_inspector,
            "screen_interactor": screen_interactor,
            "gesture_controller": gesture_controller,
            "text_controller": text_controller,
            "media_capture": media_capture,
            "video_recorder": video_recorder,
            "log_monitor": log_monitor,
            "validator": validator,
        }

    except Exception as e:
        logger.error(f"Component initialization failed: {e}")
        raise
