#!/usr/bin/env python3
"""Simple test for find_elements optimization."""

import asyncio
import json
import sys
import time
import subprocess
from pathlib import Path

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp"])
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client


async def test_find_empty():
    """Test find_elements with empty results."""
    print("Testing find_elements optimization...")

    server_params = StdioServerParameters(
        command="python3",
        args=["-m", "src.server"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Connected to server")

            # Test empty search
            start = time.time()
            result = await session.call_tool(
                name="find_elements",
                arguments={"text": "NonExistentElement12345"}
            )
            duration = time.time() - start

            if result.content:
                response = json.loads(result.content[0].text)
                print(f"Search took {duration:.2f}s")
                print(f"Success: {response.get('success')}")
                print(f"Count: {response.get('count', 0)}")
                print(f"Execution time: {response.get('execution_time', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(test_find_empty())