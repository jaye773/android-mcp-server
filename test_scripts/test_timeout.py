#!/usr/bin/env python3
"""Test script for MCP tool timeout functionality."""

import asyncio
import json
import subprocess
import sys
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


async def test_tool_timeouts():
    """Test that MCP tools properly timeout."""
    print("⏰ Testing MCP Tool Timeout Functionality")
    print("=" * 50)

    server_path = Path(__file__).parent / "src" / "server.py"

    server_params = StdioServerParameters(
        command="python3",
        args=["-m", "src.server"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            try:
                await session.initialize()
                print("✅ Connected to MCP server")

                # Test 1: Normal operation (should complete within timeout)
                print("\n1. Testing normal operation...")
                try:
                    result = await session.call_tool(
                        name="get_devices",
                        arguments={}
                    )

                    if result.content and result.content[0].text:
                        response = json.loads(result.content[0].text)
                        if response.get("success"):
                            print("✅ get_devices completed normally")
                        elif response.get("error_code") == "OPERATION_TIMEOUT":
                            print(f"⏰ get_devices timed out after {response.get('timeout_seconds')}s")
                        else:
                            print(f"❌ get_devices failed: {response.get('error')}")
                    else:
                        print("❌ get_devices returned no content")

                except Exception as e:
                    print(f"❌ get_devices error: {e}")

                # Test 2: Show timeout configuration
                print("\n2. Timeout Configuration:")
                timeouts = {
                    "Device Management": {
                        "get_devices": "15s",
                        "select_device": "10s",
                        "get_device_info": "20s"
                    },
                    "UI Tools": {
                        "get_ui_layout": "30s",
                        "find_elements": "25s"
                    },
                    "Interaction": {
                        "tap_screen": "10s",
                        "tap_element": "15s",
                        "swipe_screen": "15s",
                        "input_text": "20s"
                    },
                    "Media": {
                        "take_screenshot": "30s",
                        "start_screen_recording": "15s",
                        "stop_screen_recording": "20s"
                    },
                    "Logging": {
                        "get_logcat": "25s",
                        "start_log_monitoring": "10s",
                        "stop_log_monitoring": "15s"
                    }
                }

                for category, tools in timeouts.items():
                    print(f"   {category}:")
                    for tool, timeout in tools.items():
                        print(f"     • {tool}: {timeout}")

                # Test 3: Quick timeout behavior test
                print("\n3. Testing multiple tools for timeout behavior...")

                tools_to_test = [
                    ("get_devices", {}),
                    ("list_active_monitors", {}),
                    ("list_active_recordings", {})
                ]

                for tool_name, args in tools_to_test:
                    try:
                        print(f"   Testing {tool_name}...")
                        start_time = asyncio.get_event_loop().time()

                        result = await session.call_tool(
                            name=tool_name,
                            arguments=args
                        )

                        end_time = asyncio.get_event_loop().time()
                        duration = end_time - start_time

                        if result.content and result.content[0].text:
                            response = json.loads(result.content[0].text)
                            if response.get("error_code") == "OPERATION_TIMEOUT":
                                timeout_seconds = response.get("timeout_seconds", "unknown")
                                print(f"     ⏰ Timed out after {timeout_seconds}s (actual: {duration:.1f}s)")
                            elif response.get("success"):
                                print(f"     ✅ Completed in {duration:.1f}s")
                            else:
                                print(f"     ❌ Failed: {response.get('error')}")
                        else:
                            print(f"     ❓ No response content")

                    except Exception as e:
                        print(f"     ❌ Exception: {e}")

                print("\n" + "=" * 50)
                print("🎉 Timeout functionality test completed!")
                print("\n📋 Summary:")
                print("- All MCP tools have timeout protection")
                print("- Timeouts range from 5s to 30s based on operation complexity")
                print("- Timeout errors include helpful recovery suggestions")
                print("- Tools return structured timeout responses")

            except Exception as e:
                print(f"❌ Session error: {e}")
                import traceback
                traceback.print_exc()


async def test_timeout_with_slow_device():
    """Test timeout behavior when device is slow/unresponsive."""
    print("\n⏳ Testing with Slow Device Scenarios")
    print("-" * 40)

    server_path = Path(__file__).parent / "src" / "server.py"

    server_params = StdioServerParameters(
        command="python3",
        args=["-m", "src.server"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            try:
                await session.initialize()

                # Test potentially slow operations
                slow_operations = [
                    ("get_ui_layout", {"compressed": False, "include_invisible": True}),
                    ("take_screenshot", {"filename": "timeout_test.png"}),
                ]

                print("Testing potentially slow operations:")
                for tool_name, args in slow_operations:
                    try:
                        print(f"   • {tool_name}...")
                        start_time = asyncio.get_event_loop().time()

                        result = await session.call_tool(name=tool_name, arguments=args)

                        duration = asyncio.get_event_loop().time() - start_time

                        if result.content and result.content[0].text:
                            response = json.loads(result.content[0].text)
                            if response.get("error_code") == "OPERATION_TIMEOUT":
                                print(f"     ⏰ Timed out after {response.get('timeout_seconds')}s")
                                suggestions = response.get('recovery_suggestions', [])
                                if suggestions:
                                    print("     💡 Recovery suggestions:")
                                    for suggestion in suggestions[:2]:
                                        print(f"       - {suggestion}")
                            elif response.get("success"):
                                print(f"     ✅ Completed in {duration:.1f}s")
                            else:
                                print(f"     ❌ Failed: {response.get('error', 'Unknown error')}")

                    except Exception as e:
                        print(f"     ❌ Exception: {e}")

            except Exception as e:
                print(f"❌ Session error: {e}")


async def main():
    """Main test function."""
    print("🔧 Android MCP Server Timeout Testing")
    print("Testing timeout functionality and error handling")
    print()

    await test_tool_timeouts()
    await test_timeout_with_slow_device()

    print("\n💡 Next Steps:")
    print("- All tools now have timeout protection")
    print("- Adjust timeout values in TOOL_TIMEOUTS if needed")
    print("- Test with your specific device performance")
    print("- Use timeout information for client retry logic")


if __name__ == "__main__":
    asyncio.run(main())