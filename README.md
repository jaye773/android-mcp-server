# Android MCP Server

[![CI](https://github.com/username/android-mcp-server/workflows/CI/badge.svg)](https://github.com/username/android-mcp-server/actions)
[![codecov](https://codecov.io/gh/username/android-mcp-server/branch/main/graph/badge.svg)](https://codecov.io/gh/username/android-mcp-server)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

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

## 🔌 MCP Server Installation

### Add to Claude Desktop (Recommended)

1. **Locate your Claude Desktop configuration file**:
   ```bash
   # macOS
   ~/Library/Application Support/Claude/claude_desktop_config.json

   # Windows
   %APPDATA%/Claude/claude_desktop_config.json
   ```

2. **Add the Android MCP Server**:
   ```json
   {
     "mcpServers": {
       "android-mcp-server": {
         "command": "uv",
         "args": [
           "--directory",
           "/path/to/android-mcp-server",
           "run",
           "android-mcp-server"
         ]
       }
     }
   }
   ```

3. **Restart Claude Desktop** to activate the server.

### Alternative Installation Methods

#### Using Python directly
```json
{
  "mcpServers": {
    "android-mcp-server": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/android-mcp-server"
    }
  }
}
```

#### Using pip installed package
```bash
pip install -e /path/to/android-mcp-server
```

```json
{
  "mcpServers": {
    "android-mcp-server": {
      "command": "android-mcp-server"
    }
  }
}
```

## 🤖 Usage Examples for AI Agents

### Basic Device Interaction
```
"Take a screenshot of the current Android device screen and then find all buttons containing the word 'Settings'"

"Connect to the Android device, open the Settings app by tapping on it, then take another screenshot"

"Swipe down from the top of the screen to open the notification panel, then capture what's shown"
```

### App Testing and Automation
```
"Launch the Calculator app, perform the calculation 25 + 37, and verify the result is 62"

"Test the login flow: find the username field, enter 'testuser', find the password field, enter 'password123', then tap the login button"

"Navigate through the app's main menu by tapping each menu item and taking screenshots of each page"
```

### UI Analysis and Debugging
```
"Extract the complete UI layout of the current screen and identify all clickable elements"

"Find all text input fields on this screen and tell me which ones are currently focused"

"Look for any accessibility issues by checking if buttons have proper content descriptions"
```

### Log Monitoring and Debugging
```
"Start monitoring logs for the 'MyApp' package and show me any errors that occur in the next 2 minutes"

"Get the last 50 lines of system logs with priority level Warning or higher"

"Monitor network-related logs while I perform the next action, then show me what was logged"
```

### Performance Testing
```
"Record a 30-second video of the app launch sequence, then analyze the UI responsiveness"

"Take screenshots before and after each major user action to document the user flow"

"Monitor memory usage logs while navigating through different screens of the app"
```

### Multi-Device Testing
```
"List all connected Android devices and select the one with the largest screen resolution"

"Switch to device ID 'emulator-5554' and repeat the previous test sequence"

"Compare the same UI element across different devices by taking screenshots on each"
```

## 💡 Tips for AI Agents

### Efficient Element Finding
- Always use `find_elements` before `tap_element` to verify elements exist
- Use `exact_match: false` for partial text matching when element text might vary
- Combine multiple search criteria (text + clickable_only) for more precise targeting

### Context-Aware Log Monitoring
- Limit `max_lines` to 20-200 to avoid overwhelming the AI context window
- Use specific `tag_filter` to focus on relevant app components
- Set appropriate `priority` level (I/W/E) based on the type of information needed

### Screenshot-Driven Workflows
- Take screenshots before and after actions for verification
- Use descriptive filenames that indicate the test step or app state
- Screenshots are automatically saved to `./assets/` for easy access

### Robust Automation Patterns
- Check device connection with `get_device_info` before starting automation
- Use `get_ui_layout` when element finding fails to understand the current screen structure
- Implement retry logic for intermittent UI state issues

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
# Install test dependencies
pip install -e ".[test,dev]"

# Run full test suite with coverage
python -m pytest tests/ --cov=src --cov-fail-under=80

# Run specific test categories
python -m pytest tests/ -m "unit"           # Unit tests only
python -m pytest tests/ -m "integration"    # Integration tests
python -m pytest tests/ -m "not slow"       # Skip slow tests

# Run code quality checks
make code-quality  # or run individual tools:
flake8 src
pydocstyle src --convention=google
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Related Projects

- [MCP Specification](https://modelcontextprotocol.io/)
- [Android Debug Bridge (ADB)](https://developer.android.com/tools/adb)
- [uiautomator](https://developer.android.com/training/testing/other-components/ui-automator)
