#!/usr/bin/env python3
"""Test script to verify find_elements performance with empty results."""

import asyncio
import json
import sys
import subprocess
import time
from pathlib import Path

# Install MCP if needed
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("Installing MCP client...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp"])
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client


async def test_find_elements_performance():
    """Test find_elements with non-existent elements to measure response time."""
    print("🔍 Testing find_elements Performance")
    print("=" * 40)

    server_params = StdioServerParameters(
        command="python3",
        args=["-m", "src.server"]
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✅ Connected to MCP server")

                # Test 1: Search for non-existent element
                print("\n1. Testing search for non-existent element...")
                start_time = time.time()

                result = await session.call_tool(
                    name="find_elements",
                    arguments={
                        "text": "NonExistentButton123456",
                        "exact_match": True
                    }
                )

                end_time = time.time()
                duration = end_time - start_time

                if result.content and result.content[0].text:
                    response = json.loads(result.content[0].text)
                    if response.get("success"):
                        count = response.get("count", 0)
                        print(f"✅ Found {count} elements in {duration:.2f} seconds")
                        if count == 0:
                            print(f"   🎯 Empty result returned in {duration:.2f}s")
                            if duration > 1.0:
                                print(f"   ⚠️  Took longer than expected for empty result")
                    else:
                        print(f"❌ Failed: {response.get('error')}")
                        print(f"   Duration: {duration:.2f} seconds")
                else:
                    print(f"❌ No response content, duration: {duration:.2f} seconds")

                # Test 2: Search for multiple non-existent criteria
                print("\n2. Testing multiple non-existent search criteria...")
                start_time = time.time()

                result = await session.call_tool(
                    name="find_elements",
                    arguments={
                        "text": "NonExistent",
                        "resource_id": "com.fake.app:id/fake_button",
                        "content_desc": "Fake description that does not exist"
                    }
                )

                end_time = time.time()
                duration = end_time - start_time

                if result.content and result.content[0].text:
                    response = json.loads(result.content[0].text)
                    if response.get("success"):
                        count = response.get("count", 0)
                        print(f"✅ Found {count} elements in {duration:.2f} seconds")
                    else:
                        print(f"❌ Failed: {response.get('error')}")
                        print(f"   Duration: {duration:.2f} seconds")

                # Test 3: Search with class_name only
                print("\n3. Testing class_name search (potentially slower)...")
                start_time = time.time()

                result = await session.call_tool(
                    name="find_elements",
                    arguments={
                        "class_name": "android.widget.NonExistentWidget"
                    }
                )

                end_time = time.time()
                duration = end_time - start_time

                if result.content and result.content[0].text:
                    response = json.loads(result.content[0].text)
                    if response.get("success"):
                        count = response.get("count", 0)
                        print(f"✅ Found {count} elements in {duration:.2f} seconds")
                    else:
                        print(f"❌ Failed: {response.get('error')}")
                        print(f"   Duration: {duration:.2f} seconds")

                print(f"\n📊 Performance Summary:")
                print(f"- All searches should complete quickly for empty results")
                print(f"- UI layout extraction is the main time factor")
                print(f"- Current timeout setting: 5 seconds")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_find_elements_performance())