"""Main MCP server implementation for Android device automation."""

import asyncio
import logging
import signal

from mcp.server.fastmcp import FastMCP

from .initialization import initialize_components

# Import tool registration functions
from .tools.device import register_device_tools
from .tools.interaction import register_interaction_tools
from .tools.logs import register_log_tools
from .tools.media import register_media_tools
from .tools.ui import register_ui_tools

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

# Shutdown event for clean signal handling
_shutdown_event = asyncio.Event()


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


async def _graceful_shutdown() -> None:
    """Clean up active recordings and log monitors on shutdown."""
    video_recorder = components.get("video_recorder")
    log_monitor = components.get("log_monitor")

    if video_recorder:
        try:
            await video_recorder.cleanup_all_recordings()
        except Exception as e:
            logger.warning(f"Error cleaning up recordings: {e}")

    if log_monitor:
        try:
            await log_monitor.stop_log_monitoring(monitor_id=None)
        except Exception as e:
            logger.warning(f"Error stopping log monitors: {e}")

    logger.info("Graceful shutdown complete")
    _shutdown_event.set()


def main() -> None:
    """Run the MCP server."""
    logger.info("Starting Android MCP server...")

    async def init_and_run() -> None:
        loop = asyncio.get_running_loop()
        # Fix lambda closure bug: capture sig by value with default arg
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig, lambda s=sig: asyncio.ensure_future(_graceful_shutdown())
            )

        await init_and_register()

        # Race mcp.run_stdio_async() against shutdown event
        server_task = asyncio.ensure_future(mcp.run_stdio_async())
        shutdown_task = asyncio.ensure_future(_shutdown_event.wait())

        done, pending = await asyncio.wait(
            {server_task, shutdown_task}, return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel the pending task
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    asyncio.run(init_and_run())


if __name__ == "__main__":
    main()
