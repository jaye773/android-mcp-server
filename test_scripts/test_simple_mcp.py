#!/usr/bin/env python3
"""Simple MCP logcat test - minimal version for quick testing."""

import asyncio
import json
import sys
import subprocess
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


async def quick_mcp_logcat_test():
    """Quick test of logcat via MCP protocol."""
    print("🔍 Quick MCP Logcat Test")
    print("-" * 25)

    server_path = Path(__file__).parent / "src" / "server.py"

    server_params = StdioServerParameters(
        command="python3",
        args=["-m", "src.server"]
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✅ Connected to MCP server")

                # Test get_logcat
                result = await session.call_tool(
                    name="get_logcat",
                    arguments={
                        "priority": "I",
                        "max_lines": 3
                    }
                )

                if result.content:
                    response = json.loads(result.content[0].text)
                    if response.get("success"):
                        count = response.get("entries_count", 0)
                        print(f"✅ Got {count} log entries")

                        # Show first entry
                        entries = response.get("entries", [])
                        if entries:
                            entry = entries[0]
                            level = entry.get("level", "?")
                            tag = entry.get("tag", "Unknown")
                            message = entry.get("message", "")[:50]
                            print(f"   [{level}] {tag}: {message}...")
                    else:
                        print(f"❌ Failed: {response.get('error')}")

                print("🎉 Test complete!")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(quick_mcp_logcat_test())