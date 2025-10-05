#!/usr/bin/env python3
"""
Test script for Android MCP Server logcat functionality via MCP protocol.
This script acts as an MCP client to test the server's logcat tools.
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

# Try to import MCP client - install if needed
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("❌ MCP client not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp"])
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client


async def test_logcat_via_mcp():
    """Test logcat functionality through MCP protocol."""
    print("🔍 Testing Android MCP Server Logcat via MCP Protocol")
    print("=" * 65)

    server_path = Path(__file__).parent / "src" / "server.py"

    # Server parameters for stdio connection
    server_params = StdioServerParameters(
        command="python3",
        args=["-m", "src.server"],
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            try:
                # Initialize the session
                await session.initialize()

                print("✅ Connected to Android MCP Server")

                # List available tools
                print("\n1. Listing available logcat tools...")
                tools = await session.list_tools()

                logcat_tools = [tool for tool in tools.tools if "log" in tool.name.lower()]
                print(f"✅ Found {len(logcat_tools)} logcat-related tools:")
                for tool in logcat_tools:
                    print(f"   • {tool.name}: {tool.description}")

                # Test 1: get_logcat
                print("\n2. Testing get_logcat...")
                try:
                    result = await session.call_tool(
                        name="get_logcat",
                        arguments={
                            "priority": "I",
                            "max_lines": 5,
                            "clear_first": False
                        }
                    )

                    if result.content and result.content[0].text:
                        response = json.loads(result.content[0].text)
                        if response.get("success"):
                            entries_count = response.get("entries_count", 0)
                            print(f"✅ Retrieved {entries_count} log entries")

                            # Show sample entries
                            entries = response.get("entries", [])
                            if entries:
                                print("   Latest entries:")
                                for i, entry in enumerate(entries[:3]):
                                    level = entry.get("level", "?")
                                    tag = entry.get("tag", "Unknown")
                                    message = entry.get("message", "")[:60]
                                    print(f"     [{level}] {tag}: {message}...")
                        else:
                            print(f"❌ get_logcat failed: {response.get('error', 'Unknown error')}")
                    else:
                        print("❌ get_logcat returned no content")

                except Exception as e:
                    print(f"❌ get_logcat error: {e}")

                # Test 2: start_log_monitoring
                print("\n3. Testing start_log_monitoring...")
                monitor_id = None
                try:
                    result = await session.call_tool(
                        name="start_log_monitoring",
                        arguments={
                            "priority": "E",  # Errors only
                            "output_file": "mcp_test_errors.log"
                        }
                    )

                    if result.content and result.content[0].text:
                        response = json.loads(result.content[0].text)
                        if response.get("success"):
                            monitor_id = response.get("monitor_id")
                            print(f"✅ Started log monitoring: {monitor_id}")

                            # Monitor for 3 seconds
                            print("   Monitoring errors for 3 seconds...")
                            await asyncio.sleep(3)
                        else:
                            print(f"❌ start_log_monitoring failed: {response.get('error')}")
                    else:
                        print("❌ start_log_monitoring returned no content")

                except Exception as e:
                    print(f"❌ start_log_monitoring error: {e}")

                # Test 3: list_active_monitors
                print("\n4. Testing list_active_monitors...")
                try:
                    result = await session.call_tool(
                        name="list_active_monitors",
                        arguments={}
                    )

                    if result.content and result.content[0].text:
                        response = json.loads(result.content[0].text)
                        if response.get("success"):
                            monitors = response.get("active_monitors", [])
                            count = len(monitors)
                            print(f"✅ Found {count} active monitor(s)")

                            for monitor in monitors:
                                monitor_id_display = monitor.get("monitor_id", "Unknown")
                                duration = monitor.get("duration_seconds", 0)
                                priority = monitor.get("priority", "?")
                                print(f"     • {monitor_id_display} (priority: {priority}, duration: {duration:.1f}s)")
                        else:
                            print(f"❌ list_active_monitors failed: {response.get('error')}")
                    else:
                        print("❌ list_active_monitors returned no content")

                except Exception as e:
                    print(f"❌ list_active_monitors error: {e}")

                # Test 4: stop_log_monitoring
                if monitor_id:
                    print("\n5. Testing stop_log_monitoring...")
                    try:
                        result = await session.call_tool(
                            name="stop_log_monitoring",
                            arguments={
                                "monitor_id": monitor_id
                            }
                        )

                        if result.content and result.content[0].text:
                            response = json.loads(result.content[0].text)
                            if response.get("success"):
                                duration = response.get("duration_seconds", 0)
                                entries = response.get("entries_processed", 0)
                                print(f"✅ Stopped monitoring after {duration:.1f}s, processed {entries} entries")
                            else:
                                print(f"❌ stop_log_monitoring failed: {response.get('error')}")
                        else:
                            print("❌ stop_log_monitoring returned no content")

                    except Exception as e:
                        print(f"❌ stop_log_monitoring error: {e}")

                print("\n" + "=" * 65)
                print("🎉 MCP Logcat functionality test completed!")
                print("\nTest Results Summary:")
                print("- MCP server connection: ✅")
                print("- Tool discovery: ✅")
                print("- Logcat retrieval: Check above")
                print("- Log monitoring: Check above")
                print("- Monitor management: Check above")

            except Exception as e:
                print(f"❌ Session error: {e}")
                import traceback
                traceback.print_exc()


async def test_device_connection():
    """Test basic device connection through MCP."""
    print("\n🔧 Testing Device Connection via MCP")
    print("-" * 40)

    server_path = Path(__file__).parent / "src" / "server.py"

    server_params = StdioServerParameters(
        command="python3",
        args=["-m", "src.server"],
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            try:
                await session.initialize()

                # Test device connection
                result = await session.call_tool(
                    name="get_devices",
                    arguments={}
                )

                if result.content and result.content[0].text:
                    response = json.loads(result.content[0].text)
                    if response.get("success"):
                        devices = response.get("devices", [])
                        count = response.get("count", 0)
                        print(f"✅ Found {count} Android device(s)")

                        for device in devices:
                            device_id = device.get("id", "Unknown")
                            status = device.get("status", "Unknown")
                            model = device.get("model", "Unknown")
                            print(f"   • {device_id} ({model}) - Status: {status}")

                        return count > 0
                    else:
                        print(f"❌ get_devices failed: {response.get('error')}")
                        return False
                else:
                    print("❌ get_devices returned no content")
                    return False

            except Exception as e:
                print(f"❌ Device connection test failed: {e}")
                return False


async def main():
    """Main test function."""
    print("📱 Android MCP Server Logcat Test")
    print("Testing logcat functionality via MCP protocol")
    print()

    # First test device connection
    device_connected = await test_device_connection()

    if not device_connected:
        print("\n⚠️  No Android devices found or connection failed.")
        print("Please ensure:")
        print("  1. Android device is connected via USB")
        print("  2. USB debugging is enabled")
        print("  3. ADB is installed and working ('adb devices')")
        print("  4. Device authorization is accepted")
        return

    # Run logcat tests
    await test_logcat_via_mcp()

    print("\n💡 Next Steps:")
    print("- Check the 'logs/' directory for saved log files")
    print("- Try integrating with your MCP client")
    print("- Use different log priorities (V/D/I/W/E/F)")
    print("- Test with specific tag filters")


if __name__ == "__main__":
    asyncio.run(main())