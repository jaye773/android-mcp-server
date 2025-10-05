"""Main MCP server implementation for Android device automation."""

import asyncio
import logging

from mcp.server.fastmcp import FastMCP

from .initialization import initialize_components

# Import tool registration functions
from .tools.device import register_device_tools
from .tools.interaction import register_interaction_tools
from .tools.logs import register_log_tools
from .tools.media import register_media_tools
from .tools.ui import register_ui_tools

# Re-export tool functions for testing
from .tools.device import get_device_info, get_devices, select_device  # noqa: F401
from .tools.interaction import (  # noqa: F401
    input_text,
    press_key,
    swipe_direction,
    swipe_screen,
    tap_element,
    tap_screen,
)
from .tools.logs import (  # noqa: F401
    get_logcat,
    list_active_monitors,
    start_log_monitoring,
    stop_log_monitoring,
)
from .tools.media import (  # noqa: F401
    list_active_recordings,
    start_screen_recording,
    stop_screen_recording,
    take_screenshot,
)
from .tools.ui import find_elements, get_ui_layout, list_screen_elements  # noqa: F401
from .ui_inspector import ElementFinder  # noqa: F401

# Configure logging to stderr (not stdout for STDIO transport)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("android-mcp-server")

# Component storage
components = {}


async def init_and_register() -> None:
    """Initialize components and register all MCP tools."""
    global components

    # Initialize all components
    components = await initialize_components()

    # Register all tools with the MCP server
    register_device_tools(mcp, components)
    register_ui_tools(mcp, components)
    register_interaction_tools(mcp, components)
    register_media_tools(mcp, components)
    register_log_tools(mcp, components)

    logger.info("All MCP tools registered successfully")


def main() -> None:
    """Run the MCP server."""
    logger.info("Starting Android MCP server...")

    # Initialize components and register tools before starting server
    async def init_and_run() -> None:
        await init_and_register()
        await mcp.run_stdio_async()

    asyncio.run(init_and_run())


if __name__ == "__main__":
    main()
