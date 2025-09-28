# Android MCP Server

A powerful MCP (Model Context Protocol) server that provides comprehensive Android device automation capabilities through ADB (Android Debug Bridge). This server enables AI agents and automation tools to interact with Android devices for testing, automation, and device control tasks.

https://github.com/user-attachments/assets/68f3df22-fcf1-49af-8715-fcfa05496c90


## 🚀 Features

### Device Management
- **Multi-device support**: Connect and manage multiple Android devices simultaneously
- **Auto-discovery**: Automatic device detection and selection
- **Health monitoring**: Real-time device status and connectivity checks
- **Device information**: Complete device specifications and capabilities

### UI Automation
- **Layout inspection**: Extract complete UI hierarchy with element details
- **Smart element finding**: Search UI elements by text, resource ID, content description, or class
- **Gesture control**: Tap, swipe, and multi-touch gesture support
- **Text input**: Send text and key events (back, home, menu, etc.)

### Media Capture
- **Screenshots**: High-quality screen capture with customizable options
- **Screen recording**: MP4 video recording with quality controls
- **Batch operations**: Multiple concurrent recording sessions

### Advanced Monitoring
- **Live log monitoring**: Real-time logcat streaming with filtering
- **Multi-session support**: Concurrent log monitoring with different filters
- **Export capabilities**: Save logs and media to local filesystem

## 📋 Prerequisites

### Required Software
- **Python 3.11+**: Runtime environment
- **Android SDK Platform Tools**: For ADB functionality
- **USB Debugging enabled**: On target Android devices

### ADB Setup
1. **Install Android SDK Platform Tools**:
   ```bash
   # macOS (via Homebrew)
   brew install android-platform-tools

   # Ubuntu/Debian
   sudo apt install android-tools-adb

   # Windows
   # Download from: https://developer.android.com/tools/releases/platform-tools
   ```

2. **Verify ADB installation**:
   ```bash
   adb version
   # Should output: Android Debug Bridge version x.x.x
   ```

3. **Enable USB Debugging on Android device**:
   - Go to Settings → About Phone
   - Tap "Build number" 7 times to enable Developer Options
   - Go to Settings → Developer Options
   - Enable "USB Debugging"
   - Connect device via USB and authorize when prompted

## ⚙️ Installation

### Using uv (Recommended)
```bash
git clone <repository-url>
cd android-mcp-server
uv sync
```

### Using pip
```bash
git clone <repository-url>
cd android-mcp-server
pip install -e .
```

### Verify Installation
```bash
# Check if devices are detected
adb devices

# Test server startup
python -m src.server
```

## 🚀 Quick Start

### Basic Usage Example
```python
import asyncio
from mcp import ClientSession

async def demo_automation():
    # Connect to MCP server
    session = ClientSession()

    # Get connected devices
    devices = await session.call_tool("get_devices")
    print(f"Found {devices['count']} devices")

    # Take a screenshot
    screenshot = await session.call_tool("take_screenshot", {
        "filename": "demo_screenshot.png"
    })

    # Find and tap a button
    elements = await session.call_tool("find_elements", {
        "text": "Settings",
        "clickable_only": True
    })

    if elements["count"] > 0:
        result = await session.call_tool("tap_element", {
            "text": "Settings"
        })
        print("Tapped Settings button")

# Run the demo
asyncio.run(demo_automation())
```

### Command Line Usage
```bash
# Start the MCP server
python -m src.server

# Or using the installed script
android-mcp-server
```

## 🛠️ Available Tools

### Device Management
- **`get_devices()`**: List all connected Android devices
- **`select_device(device_id?)`**: Select specific device or auto-select first available
- **`get_device_info()`**: Get detailed device information and screen specifications

### UI Interaction
- **`get_ui_layout(compressed?, include_invisible?)`**: Extract complete UI hierarchy
- **`find_elements(...)`**: Find UI elements by text, resource ID, content description, or class
- **`tap_screen(x, y)`**: Tap at specific screen coordinates
- **`tap_element(text?, resource_id?, content_desc?, index?)`**: Find and tap UI element
- **`swipe_screen(start_x, start_y, end_x, end_y, duration_ms?)`**: Swipe between coordinates
- **`swipe_direction(direction, distance?, duration_ms?)`**: Swipe in direction (up/down/left/right)
- **`input_text(text, clear_existing?)`**: Input text into focused field
- **`press_key(keycode)`**: Press device keys (BACK, HOME, ENTER, etc.)

### Media Capture
- **`take_screenshot(filename?, pull_to_local?)`**: Capture device screenshot
- **`start_screen_recording(...)`**: Start screen recording with quality options
- **`stop_screen_recording(recording_id?, pull_to_local?)`**: Stop recording session
- **`list_active_recordings()`**: List all active recording sessions

### Log Monitoring
- **`get_logcat(tag_filter?, priority?, max_lines?, clear_first?)`**: Get device logs
- **`start_log_monitoring(tag_filter?, priority?, output_file?)`**: Start continuous log monitoring
- **`stop_log_monitoring(monitor_id?)`**: Stop log monitoring session
- **`list_active_monitors()`**: List active monitoring sessions

## ⚙️ Configuration Examples

### Element Search Options
```python
# Find elements by text (partial match)
await session.call_tool("find_elements", {
    "text": "Login",
    "clickable_only": True,
    "exact_match": False
})

# Find by resource ID
await session.call_tool("find_elements", {
    "resource_id": "com.app:id/login_button",
    "enabled_only": True
})

# Find by content description (accessibility)
await session.call_tool("find_elements", {
    "content_desc": "Submit form",
    "clickable_only": True
})
```

### Screen Recording Options
```python
# High quality recording
await session.call_tool("start_screen_recording", {
    "filename": "test_session.mp4",
    "time_limit": 300,  # 5 minutes
    "bit_rate": "8M",   # 8 Mbps
    "size_limit": "1080x1920"  # Full HD
})

# Quick recording for debugging
await session.call_tool("start_screen_recording", {
    "time_limit": 60,   # 1 minute
    "bit_rate": "2M"    # Lower quality
})
```

### Log Monitoring
Tip for LLM agents (Claude/Codex/Gemini): always limit log volume to protect the model’s context window. Prefer targeted queries with `tag_filter`, `priority`, and a small `max_lines` (e.g., 50–200).
```python
# Monitor app-specific logs
await session.call_tool("start_log_monitoring", {
    "tag_filter": "MyApp",
    "priority": "I",  # Info level and above
    "output_file": "app_logs.txt"
})

# System-wide error monitoring
await session.call_tool("start_log_monitoring", {
    "priority": "E",  # Errors only
    "output_file": "system_errors.txt"
})

# Fetch a compact snapshot of recent logs (context-safe)
logs = await session.call_tool("get_logcat", {
    "tag_filter": "MyApp",     # Narrow to your app/component
    "priority": "W",           # Only warnings/errors and above
    "max_lines": 100,           # Keep small to avoid context pollution
    "clear_first": False        # Avoid clearing unless you need a clean slate
})
```

## 🔧 Troubleshooting

### Common Issues

#### Device Not Detected
```bash
# Check USB connection
adb devices

# Restart ADB server
adb kill-server
adb start-server

# Check device authorization
adb devices
# Should show "device" not "unauthorized"
```

#### Permission Denied Errors
- Ensure USB Debugging is enabled in Developer Options
- Check that device is authorized (accept the RSA key fingerprint popup)
- Try different USB cable or port

#### Screen Recording Fails
- Verify device supports screen recording (Android 4.4+)
- Check available storage space on device
- Ensure no other recording apps are running

#### UI Element Not Found
- Use `get_ui_layout()` to inspect current screen structure
- Check if element is visible and enabled
- Try partial text matching with `exact_match: false`
- Wait for UI to load before searching

### Debugging Tips

1. **Use device info to verify connection**:
   ```python
   info = await session.call_tool("get_device_info")
   print(info["screen_size"])  # Verify screen dimensions
   ```

2. **Inspect UI before automation**:
   ```python
   layout = await session.call_tool("get_ui_layout", {"compressed": False})
   # Examine element structure and attributes
   ```

3. **Monitor logs during automation**:
   ```python
   await session.call_tool("start_log_monitoring", {
       "tag_filter": "MyApp",
       "priority": "D"  # Debug and above while running flows
   })
   # Run your automation
   # Snapshot recent logs; limit volume for LLM context safety
   logs = await session.call_tool("get_logcat", {
       "tag_filter": "MyApp",
       "priority": "I",
       "max_lines": 50,
       "clear_first": False
   })
   ```

4. **Capture screenshots for verification**:
   ```python
   await session.call_tool("take_screenshot", {"filename": "before_action.png"})
   # Perform action
   await session.call_tool("take_screenshot", {"filename": "after_action.png"})
   ```

## 🏗️ Architecture

The server is built with a modular architecture:

- **`ADBManager`**: Core ADB communication and device management
- **`UILayoutExtractor`**: UI hierarchy parsing and element extraction
- **`ScreenInteractor`**: Touch and gesture handling
- **`MediaCapture`**: Screenshot and recording functionality
- **`LogMonitor`**: Real-time log monitoring and filtering
- **`FastMCP`**: MCP protocol implementation and tool registration

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

### Development Setup
```bash
git clone <repository-url>
cd android-mcp-server
uv sync --dev
```

### Running Tests
```bash
# Run with connected Android device
python -m pytest tests/
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Related Projects

- [MCP Specification](https://modelcontextprotocol.io/)
- [Android Debug Bridge (ADB)](https://developer.android.com/tools/adb)
- [uiautomator](https://developer.android.com/training/testing/other-components/ui-automator)
