#!/usr/bin/env python3
"""List available MCP tools to understand parameter structure."""

import asyncio
import subprocess
import sys

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp"])
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client


async def list_tools():
    """List available MCP tools."""
    print("Listing MCP tools...")

    server_params = StdioServerParameters(
        command="python3",
        args=["-m", "src.server"]
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("Connected to server")

                # List tools
                tools = await session.list_tools()
                print(f"Found {len(tools.tools)} tools")

                for tool in tools.tools:
                    if tool.name == "find_elements":
                        print(f"\nTool: {tool.name}")
                        print(f"Description: {tool.description}")
                        print(f"Input schema: {tool.inputSchema}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(list_tools())