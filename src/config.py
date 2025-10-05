"""Configuration constants for Android MCP server."""

import logging

# Configure logging to stderr (not stdout for STDIO transport)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

# Timeout configuration for MCP tools (in seconds)
TOOL_TIMEOUTS = {
    # Device management tools
    "get_devices": 15,
    "select_device": 10,
    "get_device_info": 20,
    # UI tools
    "get_ui_layout": 10,
    "list_screen_elements": 10,
    "find_elements": 8,
    # Interaction tools
    "tap_screen": 5,
    "tap_element": 10,
    "swipe_screen": 15,
    "swipe_direction": 15,
    "input_text": 20,
    "press_key": 10,
    # Media tools
    "take_screenshot": 8,
    "start_screen_recording": 15,
    "stop_screen_recording": 20,
    "list_active_recordings": 5,
    # Log tools
    "get_logcat": 10,
    "start_log_monitoring": 10,
    "stop_log_monitoring": 15,
    "list_active_monitors": 5,
}

DEFAULT_TOOL_TIMEOUT = 30  # Default timeout for tools not in the list
