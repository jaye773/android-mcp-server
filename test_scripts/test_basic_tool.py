#!/usr/bin/env python3
"""Test basic MCP tool to verify connection."""

import asyncio
import json
import subprocess
import sys

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp"])
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client


async def test_basic_tool():
    """Test basic MCP tool."""
    print("Testing basic MCP tool...")

    server_params = StdioServerParameters(
        command="python3",
        args=["-m", "src.server"]
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("Connected to server")

                # Test get_devices (should work)
                result = await session.call_tool(
                    name="get_devices",
                    arguments={}
                )

                print(f"Result content: {result.content}")
                if result.content and result.content[0].text:
                    response = json.loads(result.content[0].text)
                    print(f"Success: {response.get('success')}")
                else:
                    print("No content in response")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_basic_tool())