#!/usr/bin/env python3
"""Simple logcat test for Android MCP Server."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def quick_logcat_test():
    """Quick test of logcat functionality."""
    try:
        from src.adb_manager import ADBManager
        from src.log_monitor import LogMonitor

        print("🔍 Quick Logcat Test")
        print("-" * 30)

        # Initialize
        adb = ADBManager()
        monitor = LogMonitor(adb)

        # Check device
        devices = await adb.list_devices()
        if not devices:
            print("❌ No devices found. Connect Android device with USB debugging.")
            return

        result = await adb.auto_select_device()
        if not result["success"]:
            print(f"❌ Device selection failed: {result['error']}")
            return

        print(f"✅ Device: {result['selected']['id']}")

        # Get recent logs
        print("\n📋 Getting recent logs...")
        logs = await monitor.get_logcat(priority="I", max_lines=5)

        if logs["success"]:
            print(f"✅ Found {logs['entries_count']} log entries")
            for entry in logs["entries"][:3]:
                print(f"  [{entry['level']}] {entry['tag']}: {entry['message'][:60]}...")
        else:
            print(f"❌ Logcat failed: {logs.get('error')}")

        print("\n🎉 Test complete!")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(quick_logcat_test())