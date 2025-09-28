#!/usr/bin/env python3
"""
Test script for Android MCP Server logcat functionality.
This script demonstrates how to use the logcat tools.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.adb_manager import ADBManager
from src.log_monitor import LogMonitor


async def test_logcat_functionality():
    """Test various logcat operations."""
    print("🔍 Testing Android MCP Server Logcat Functionality")
    print("=" * 60)

    # Initialize components
    adb_manager = ADBManager()
    log_monitor = LogMonitor(adb_manager)

    try:
        # 1. Check device connection
        print("\n1. Checking device connection...")
        devices = await adb_manager.list_devices()
        if not devices:
            print("❌ No Android devices found!")
            print("Please connect an Android device with USB debugging enabled.")
            return

        # Auto-select device
        selection = await adb_manager.auto_select_device()
        if not selection["success"]:
            print(f"❌ Device selection failed: {selection['error']}")
            return

        print(f"✅ Connected to device: {selection['selected']['id']}")

        # 2. Test basic logcat
        print("\n2. Testing basic logcat retrieval...")
        logcat_result = await log_monitor.get_logcat(
            priority="I",  # Info level and above
            max_lines=10
        )

        if logcat_result["success"]:
            print(f"✅ Retrieved {logcat_result['entries_count']} log entries")
            if logcat_result["entries"]:
                print("Latest log entry:")
                latest = logcat_result["entries"][0]
                print(f"  [{latest['level']}] {latest['tag']}: {latest['message'][:100]}...")
        else:
            print(f"❌ Logcat failed: {logcat_result.get('error', 'Unknown error')}")

        # 3. Test filtered logcat
        print("\n3. Testing filtered logcat (System logs only)...")
        system_logs = await log_monitor.get_logcat(
            tag_filter="System",
            priority="W",  # Warning and above
            max_lines=5
        )

        if system_logs["success"]:
            print(f"✅ Retrieved {system_logs['entries_count']} system log entries")
        else:
            print(f"⚠️  System logs: {system_logs.get('error', 'No system logs found')}")

        # 4. Test log monitoring (brief)
        print("\n4. Testing log monitoring...")
        monitor_result = await log_monitor.start_log_monitoring(
            priority="E",  # Errors only
            output_file="test_errors.log"
        )

        if monitor_result["success"]:
            monitor_id = monitor_result["monitor_id"]
            print(f"✅ Started log monitoring: {monitor_id}")

            # Monitor for 3 seconds
            print("   Monitoring for 3 seconds...")
            await asyncio.sleep(3)

            # Stop monitoring
            stop_result = await log_monitor.stop_log_monitoring(monitor_id)
            if stop_result["success"]:
                print(f"✅ Stopped monitoring after {stop_result['duration_seconds']:.1f}s")
                print(f"   Processed {stop_result['entries_processed']} entries")
            else:
                print(f"⚠️  Stop monitoring failed: {stop_result.get('error')}")
        else:
            print(f"❌ Monitor start failed: {monitor_result.get('error')}")

        # 5. Test log search
        print("\n5. Testing log search...")
        search_result = await log_monitor.search_logs(
            search_term="android",
            priority="I",
            max_results=5
        )

        if search_result["success"]:
            print(f"✅ Found {search_result['matches_found']} matches for 'android'")
            if search_result["entries"]:
                print("First match:")
                match = search_result["entries"][0]
                print(f"  [{match['level']}] {match['tag']}: {match['message'][:80]}...")
        else:
            print(f"⚠️  Search failed: {search_result.get('error')}")

        # 6. List active monitors
        print("\n6. Checking active monitors...")
        active_result = await log_monitor.list_active_monitors()
        if active_result["success"]:
            count = active_result["count"]
            print(f"✅ Active monitors: {count}")
        else:
            print(f"⚠️  List monitors failed: {active_result.get('error')}")

        print("\n" + "=" * 60)
        print("🎉 Logcat functionality test completed!")
        print("\nNext steps:")
        print("- Check the 'logs/' directory for saved log files")
        print("- Try the MCP server with: python -m src.server")
        print("- Use logcat tools in your MCP client")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


async def test_logcat_with_mcp_server():
    """Test logcat through the MCP server interface."""
    print("\n🔧 Testing Logcat via MCP Server Interface")
    print("=" * 50)

    try:
        # Import server components
        from src.server import (
            initialize_components,
            get_logcat,
            start_log_monitoring,
            stop_log_monitoring,
            list_active_monitors,
            LogcatParams,
            LogMonitorParams,
            StopMonitorParams
        )

        # Initialize server components
        await initialize_components()

        # Test get_logcat tool
        print("\n1. Testing get_logcat MCP tool...")
        params = LogcatParams(
            priority="I",
            max_lines=5,
            clear_first=False
        )

        result = await get_logcat(params)
        if result["success"]:
            print(f"✅ MCP get_logcat: {result['entries_count']} entries")
        else:
            print(f"❌ MCP get_logcat failed: {result.get('error')}")

        # Test start_log_monitoring tool
        print("\n2. Testing start_log_monitoring MCP tool...")
        monitor_params = LogMonitorParams(
            priority="W",
            output_file="mcp_test_monitor.log"
        )

        monitor_result = await start_log_monitoring(monitor_params)
        if monitor_result["success"]:
            monitor_id = monitor_result["monitor_id"]
            print(f"✅ MCP monitor started: {monitor_id}")

            # Brief monitoring
            await asyncio.sleep(2)

            # Stop monitoring
            stop_params = StopMonitorParams(monitor_id=monitor_id)
            stop_result = await stop_log_monitoring(stop_params)
            if stop_result["success"]:
                print(f"✅ MCP monitor stopped: {stop_result['duration_seconds']:.1f}s")
        else:
            print(f"❌ MCP monitor failed: {monitor_result.get('error')}")

        print("✅ MCP server logcat test completed!")

    except Exception as e:
        print(f"❌ MCP server test failed: {e}")


def print_usage():
    """Print usage instructions."""
    print("""
Android MCP Server Logcat Test

Usage:
  python test_logcat.py [option]

Options:
  basic    - Test basic logcat functionality (default)
  mcp      - Test logcat through MCP server interface
  help     - Show this help message

Prerequisites:
  - Android device connected via USB
  - USB debugging enabled
  - ADB installed and in PATH

Examples:
  python test_logcat.py
  python test_logcat.py basic
  python test_logcat.py mcp
    """)


async def main():
    """Main test function."""
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "basic"

    if mode == "help":
        print_usage()
        return
    elif mode == "mcp":
        await test_logcat_functionality()
        await test_logcat_with_mcp_server()
    else:
        await test_logcat_functionality()


if __name__ == "__main__":
    asyncio.run(main())