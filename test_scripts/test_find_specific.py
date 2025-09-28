#!/usr/bin/env python3
"""Test find_elements specifically."""

import asyncio
import json
import subprocess
import sys
import time

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp"])
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client


async def test_find_elements():
    """Test find_elements specifically."""
    print("Testing find_elements...")

    server_params = StdioServerParameters(
        command="python3",
        args=["-m", "src.server"]
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("Connected to server")

                # Test find_elements
                start = time.time()
                result = await session.call_tool(
                    name="find_elements",
                    arguments={
                        "params": {
                            "text": "Create slideshows",
                            "exact_match": True,
                            "clickable_only": False,
                            "enabled_only": True
                        }
                    }
                )
                duration = time.time() - start

                print(f"Duration: {duration:.2f}s")
                print(f"Result content type: {type(result.content)}")

                if result.content:
                    print(f"Content length: {len(result.content)}")
                    if result.content[0].text:
                        print(f"Text content: {result.content[0].text}")
                        try:
                            response = json.loads(result.content[0].text)
                            print(f"Success: {response.get('success')}")
                            print(f"Count: {response.get('count', 0)}")
                            print(f"Execution time: {response.get('execution_time', 'N/A')}")
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}")
                    else:
                        print("No text content")
                else:
                    print("No content in response")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_find_elements())