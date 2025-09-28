# Android MCP Server API Reference

A comprehensive reference for all MCP tools provided by the Android MCP Server for automating Android device interactions.

## Table of Contents

1. [Overview](#overview)
2. [Response Format](#response-format)
3. [Error Codes](#error-codes)
4. [Device Management](#device-management)
5. [UI Inspection](#ui-inspection)
6. [Screen Interaction](#screen-interaction)
7. [Media Capture](#media-capture)
8. [Log Monitoring](#log-monitoring)
9. [Common Usage Patterns](#common-usage-patterns)

## Overview

The Android MCP Server provides 18 tools organized into 5 categories for comprehensive Android device automation:

- **Device Management**: Connect to and manage Android devices
- **UI Inspection**: Extract and analyze UI hierarchy and elements
- **Screen Interaction**: Perform taps, swipes, and input operations
- **Media Capture**: Take screenshots and record screen videos
- **Log Monitoring**: Monitor and analyze device logs

All tools are asynchronous and return standardized JSON responses with success indicators and detailed error information.

## Response Format

### Standard Response Structure

All API tools return responses following this standard structure:

```json
{
  "success": boolean,
  "error": string,          // Present when success = false
  "data": object,           // Tool-specific response data
  "timestamp": string       // ISO timestamp (when applicable)
}
```

### Success Response Example
```json
{
  "success": true,
  "devices": [
    {
      "id": "emulator-5554",
      "status": "device",
      "product": "sdk_gphone64_x86_64"
    }
  ],
  "count": 1
}
```

### Error Response Example
```json
{
  "success": false,
  "error": "No devices found. Please ensure ADB is running and device is connected."
}
```

## Error Codes

### Common Error Categories

| Error Type | Description | Common Causes | Resolution |
|------------|-------------|---------------|------------|
| `ADB_CONNECTION_ERROR` | Cannot connect to ADB daemon | ADB not running, no USB debugging | Start ADB, enable USB debugging |
| `DEVICE_NOT_FOUND` | Specified device not available | Device disconnected, wrong device ID | Check device connection, verify device ID |
| `UI_DUMP_FAILED` | Cannot extract UI hierarchy | Device locked, permission issues | Unlock device, check permissions |
| `ELEMENT_NOT_FOUND` | UI element not located | Element doesn't exist, timing issues | Verify element exists, add wait time |
| `INTERACTION_FAILED` | Touch/input operation failed | Screen off, app not responsive | Wake device, check app state |
| `MEDIA_CAPTURE_ERROR` | Screenshot/recording failed | Storage full, permission denied | Free storage space, check permissions |
| `LOG_ACCESS_ERROR` | Cannot access device logs | Insufficient permissions | Enable developer options, check ADB permissions |

### Specific Error Messages

```json
// Device connection errors
{
  "success": false,
  "error": "ADB daemon not running. Please start ADB server."
}

// UI interaction errors
{
  "success": false,
  "error": "Element with text 'Login' not found. Available elements: ['Sign In', 'Register', 'Forgot Password']"
}

// Media capture errors
{
  "success": false,
  "error": "Screenshot failed: Device storage full. Available: 0MB, Required: 5MB"
}
```

---

## Device Management

Tools for connecting to and managing Android devices via ADB.

### get_devices

List all connected Android devices available through ADB.

**Parameters:** None

**Response Format:**
```json
{
  "success": boolean,
  "devices": [
    {
      "id": string,           // Device identifier (e.g., "emulator-5554")
      "status": string,       // Device status ("device", "offline", "unauthorized")
      "product": string,      // Device product name
      "model": string,        // Device model (when available)
      "transport_id": string  // ADB transport identifier
    }
  ],
  "count": number
}
```

**Usage Example:**
```json
// Request
{
  "tool": "get_devices",
  "parameters": {}
}

// Response
{
  "success": true,
  "devices": [
    {
      "id": "emulator-5554",
      "status": "device",
      "product": "sdk_gphone64_x86_64",
      "model": "sdk_gphone64_x86_64",
      "transport_id": "1"
    },
    {
      "id": "RF8M7028XZJ",
      "status": "device",
      "product": "flame",
      "model": "Pixel 4",
      "transport_id": "2"
    }
  ],
  "count": 2
}
```

**Error Scenarios:**
- ADB daemon not running
- No devices connected
- Permission issues

---

### select_device

Select an Android device for operations. Auto-selects the first available device if none specified.

**Parameters:**
```json
{
  "device_id": string | null  // Optional: Specific device ID to select
}
```

**Parameter Details:**
- `device_id`: Device identifier from `get_devices` response. If null/omitted, auto-selects first available device.

**Response Format:**
```json
{
  "success": boolean,
  "selected_device": string,    // ID of selected device
  "health": {
    "responsive": boolean,      // Device responds to ADB commands
    "screen_on": boolean,       // Screen is on/awake
    "unlocked": boolean,        // Device is unlocked (when detectable)
    "battery_level": number,    // Battery percentage (0-100)
    "temperature": number       // Device temperature in Celsius
  }
}
```

**Usage Examples:**
```json
// Auto-select first device
{
  "tool": "select_device",
  "parameters": {}
}

// Select specific device
{
  "tool": "select_device",
  "parameters": {
    "device_id": "RF8M7028XZJ"
  }
}

// Response
{
  "success": true,
  "selected_device": "RF8M7028XZJ",
  "health": {
    "responsive": true,
    "screen_on": true,
    "unlocked": true,
    "battery_level": 85,
    "temperature": 32.5
  }
}
```

**Error Scenarios:**
- Specified device not found
- Device offline or unauthorized
- Health check failures

---

### get_device_info

Get comprehensive information about the currently selected device.

**Parameters:** None

**Response Format:**
```json
{
  "success": boolean,
  "device_info": {
    "manufacturer": string,     // Device manufacturer
    "model": string,           // Device model
    "brand": string,           // Device brand
    "product": string,         // Product identifier
    "android_version": string, // Android OS version
    "sdk_version": number,     // Android SDK API level
    "serial": string,          // Device serial number
    "cpu_abi": string         // Primary CPU architecture
  },
  "screen_size": {
    "width": number,           // Screen width in pixels
    "height": number,          // Screen height in pixels
    "density": number          // Screen density (DPI)
  },
  "health": {
    "responsive": boolean,
    "screen_on": boolean,
    "unlocked": boolean,
    "battery_level": number,
    "temperature": number
  }
}
```

**Usage Example:**
```json
// Request
{
  "tool": "get_device_info",
  "parameters": {}
}

// Response
{
  "success": true,
  "device_info": {
    "manufacturer": "Google",
    "model": "Pixel 4",
    "brand": "google",
    "product": "flame",
    "android_version": "13",
    "sdk_version": 33,
    "serial": "RF8M7028XZJ",
    "cpu_abi": "arm64-v8a"
  },
  "screen_size": {
    "width": 1080,
    "height": 2280,
    "density": 440
  },
  "health": {
    "responsive": true,
    "screen_on": true,
    "unlocked": true,
    "battery_level": 85,
    "temperature": 32.5
  }
}
```

**Error Scenarios:**
- No device selected
- Device disconnected
- Permission denied for device info access

---

## UI Inspection

Tools for extracting and analyzing the user interface hierarchy and elements.

### get_ui_layout

Extract the complete UI hierarchy using Android's uiautomator dump functionality.

**Parameters:**
```json
{
  "compressed": boolean,        // Default: true - Use compressed XML format
  "include_invisible": boolean  // Default: false - Include invisible/hidden elements
}
```

**Parameter Details:**
- `compressed`: When true, generates smaller XML without formatting (recommended for performance)
- `include_invisible`: When true, includes elements that are not currently visible on screen

**Response Format:**
```json
{
  "success": boolean,
  "elements": [
    {
      "class": string,              // Element class name (e.g., "android.widget.Button")
      "resource_id": string,        // Resource ID (e.g., "com.app:id/login_button")
      "text": string,               // Visible text content
      "content_desc": string,       // Content description for accessibility
      "bounds": {
        "left": number,             // Left boundary in pixels
        "top": number,              // Top boundary in pixels
        "right": number,            // Right boundary in pixels
        "bottom": number            // Bottom boundary in pixels
      },
      "center": {
        "x": number,                // Center X coordinate
        "y": number                 // Center Y coordinate
      },
      "clickable": boolean,         // Element can be clicked
      "enabled": boolean,           // Element is enabled for interaction
      "focused": boolean,           // Element currently has focus
      "selected": boolean,          // Element is selected
      "checkable": boolean,         // Element can be checked/unchecked
      "checked": boolean,           // Element is currently checked
      "scrollable": boolean,        // Element can be scrolled
      "password": boolean,          // Element is a password field
      "index": number,              // Element index within parent
      "package": string             // App package name
    }
  ],
  "element_count": number,          // Total number of elements found
  "dump_time": number,              // Time taken for UI dump (milliseconds)
  "screen_size": {
    "width": number,
    "height": number
  }
}
```

**Usage Examples:**
```json
// Get compressed layout (default)
{
  "tool": "get_ui_layout",
  "parameters": {
    "compressed": true,
    "include_invisible": false
  }
}

// Get full layout including invisible elements
{
  "tool": "get_ui_layout",
  "parameters": {
    "compressed": false,
    "include_invisible": true
  }
}

// Response example
{
  "success": true,
  "elements": [
    {
      "class": "android.widget.Button",
      "resource_id": "com.example.app:id/login_btn",
      "text": "Login",
      "content_desc": "Login button",
      "bounds": {
        "left": 100,
        "top": 200,
        "right": 300,
        "bottom": 250
      },
      "center": {
        "x": 200,
        "y": 225
      },
      "clickable": true,
      "enabled": true,
      "focused": false,
      "selected": false,
      "checkable": false,
      "checked": false,
      "scrollable": false,
      "password": false,
      "index": 2,
      "package": "com.example.app"
    }
  ],
  "element_count": 45,
  "dump_time": 250,
  "screen_size": {
    "width": 1080,
    "height": 2280
  }
}
```

**Error Scenarios:**
- UI dump service not available
- Screen locked or off
- App not responding
- Insufficient permissions

---

### find_elements

Search for specific UI elements using various criteria with flexible matching options.

**Parameters:**
```json
{
  "text": string | null,          // Text content to search for
  "resource_id": string | null,   // Resource ID to match
  "content_desc": string | null,  // Content description to match
  "class_name": string | null,    // Class name to match
  "clickable_only": boolean,      // Default: false - Only return clickable elements
  "enabled_only": boolean,        // Default: true - Only return enabled elements
  "exact_match": boolean          // Default: false - Use exact vs. partial string matching
}
```

**Parameter Details:**
- `text`: Searches element text content (supports partial matching by default)
- `resource_id`: Matches resource identifier (e.g., "com.app:id/button")
- `content_desc`: Matches accessibility content description
- `class_name`: Matches Android class name (e.g., "android.widget.Button")
- `clickable_only`: When true, filters to only interactive elements
- `enabled_only`: When true, excludes disabled elements
- `exact_match`: When true, requires exact string matches instead of partial

**Response Format:**
```json
{
  "success": boolean,
  "elements": [
    // Same element structure as get_ui_layout
  ],
  "count": number,                  // Number of matching elements
  "search_criteria": {              // Echo of search parameters used
    "text": string,
    "resource_id": string,
    "content_desc": string,
    "class_name": string,
    "clickable_only": boolean,
    "enabled_only": boolean,
    "exact_match": boolean
  }
}
```

**Usage Examples:**
```json
// Find buttons with "Login" text
{
  "tool": "find_elements",
  "parameters": {
    "text": "Login",
    "clickable_only": true
  }
}

// Find by resource ID
{
  "tool": "find_elements",
  "parameters": {
    "resource_id": "com.example.app:id/submit_btn"
  }
}

// Find all EditText fields
{
  "tool": "find_elements",
  "parameters": {
    "class_name": "android.widget.EditText",
    "enabled_only": true
  }
}

// Exact text match
{
  "tool": "find_elements",
  "parameters": {
    "text": "Sign In",
    "exact_match": true
  }
}

// Response example
{
  "success": true,
  "elements": [
    {
      "class": "android.widget.Button",
      "resource_id": "com.example.app:id/login_btn",
      "text": "Login",
      "content_desc": "Login button",
      "bounds": {
        "left": 100,
        "top": 200,
        "right": 300,
        "bottom": 250
      },
      "center": {
        "x": 200,
        "y": 225
      },
      "clickable": true,
      "enabled": true
    }
  ],
  "count": 1,
  "search_criteria": {
    "text": "Login",
    "resource_id": null,
    "content_desc": null,
    "class_name": null,
    "clickable_only": true,
    "enabled_only": true,
    "exact_match": false
  }
}
```

**Error Scenarios:**
- No elements match search criteria
- UI dump fails during search
- Invalid search parameters

---

## Screen Interaction

Tools for performing touch interactions, gestures, and input operations.

### tap_screen

Perform a tap gesture at specific screen coordinates.

**Parameters:**
```json
{
  "x": number,    // X coordinate in pixels (required)
  "y": number     // Y coordinate in pixels (required)
}
```

**Parameter Details:**
- `x`: Horizontal position from left edge of screen (0 to screen width)
- `y`: Vertical position from top edge of screen (0 to screen height)

**Response Format:**
```json
{
  "success": boolean,
  "action": "tap_coordinates",
  "coordinates": {
    "x": number,
    "y": number
  },
  "execution_time": number,    // Time taken in milliseconds
  "screen_size": {
    "width": number,
    "height": number
  }
}
```

**Usage Example:**
```json
// Tap at center of 1080x2280 screen
{
  "tool": "tap_screen",
  "parameters": {
    "x": 540,
    "y": 1140
  }
}

// Response
{
  "success": true,
  "action": "tap_coordinates",
  "coordinates": {
    "x": 540,
    "y": 1140
  },
  "execution_time": 45,
  "screen_size": {
    "width": 1080,
    "height": 2280
  }
}
```

**Error Scenarios:**
- Coordinates outside screen bounds
- Screen locked or off
- Touch input disabled
- Device not responding

---

### tap_element

Find and tap a UI element using various search criteria.

**Parameters:**
```json
{
  "text": string | null,          // Text content to find and tap
  "resource_id": string | null,   // Resource ID to find and tap
  "content_desc": string | null,  // Content description to find and tap
  "index": number                 // Default: 0 - Index of element if multiple matches
}
```

**Parameter Details:**
- `text`: Searches for element containing this text (partial match supported)
- `resource_id`: Matches exact resource identifier
- `content_desc`: Matches accessibility description
- `index`: When multiple elements match, selects by index (0-based)

**Response Format:**
```json
{
  "success": boolean,
  "action": "tap_element",
  "element_found": {
    "class": string,
    "resource_id": string,
    "text": string,
    "bounds": object,
    "center": object
  },
  "tap_coordinates": {
    "x": number,
    "y": number
  },
  "search_criteria": object,
  "execution_time": number
}
```

**Usage Examples:**
```json
// Tap button with "Login" text
{
  "tool": "tap_element",
  "parameters": {
    "text": "Login"
  }
}

// Tap by resource ID
{
  "tool": "tap_element",
  "parameters": {
    "resource_id": "com.example.app:id/submit_btn"
  }
}

// Tap second matching element
{
  "tool": "tap_element",
  "parameters": {
    "text": "Cancel",
    "index": 1
  }
}

// Response example
{
  "success": true,
  "action": "tap_element",
  "element_found": {
    "class": "android.widget.Button",
    "resource_id": "com.example.app:id/login_btn",
    "text": "Login",
    "bounds": {
      "left": 100,
      "top": 200,
      "right": 300,
      "bottom": 250
    },
    "center": {
      "x": 200,
      "y": 225
    }
  },
  "tap_coordinates": {
    "x": 200,
    "y": 225
  },
  "search_criteria": {
    "text": "Login",
    "resource_id": null,
    "content_desc": null,
    "index": 0
  },
  "execution_time": 120
}
```

**Error Scenarios:**
- Element not found
- Element not clickable or enabled
- Multiple matches found (use index parameter)
- Element coordinates outside screen

---

### swipe_screen

Perform a swipe gesture between two specific coordinates.

**Parameters:**
```json
{
  "start_x": number,      // Start X coordinate (required)
  "start_y": number,      // Start Y coordinate (required)
  "end_x": number,        // End X coordinate (required)
  "end_y": number,        // End Y coordinate (required)
  "duration_ms": number   // Default: 300 - Swipe duration in milliseconds
}
```

**Parameter Details:**
- `start_x`, `start_y`: Starting position of swipe gesture
- `end_x`, `end_y`: Ending position of swipe gesture
- `duration_ms`: Duration of swipe animation (100-2000ms recommended)

**Response Format:**
```json
{
  "success": boolean,
  "action": "swipe_coordinates",
  "start_coordinates": {
    "x": number,
    "y": number
  },
  "end_coordinates": {
    "x": number,
    "y": number
  },
  "duration_ms": number,
  "distance": number,       // Distance in pixels
  "direction": string,      // Calculated direction (up/down/left/right/diagonal)
  "execution_time": number
}
```

**Usage Examples:**
```json
// Swipe up from bottom center
{
  "tool": "swipe_screen",
  "parameters": {
    "start_x": 540,
    "start_y": 2000,
    "end_x": 540,
    "end_y": 1000,
    "duration_ms": 500
  }
}

// Quick swipe right
{
  "tool": "swipe_screen",
  "parameters": {
    "start_x": 200,
    "start_y": 1140,
    "end_x": 800,
    "end_y": 1140,
    "duration_ms": 200
  }
}

// Response example
{
  "success": true,
  "action": "swipe_coordinates",
  "start_coordinates": {
    "x": 540,
    "y": 2000
  },
  "end_coordinates": {
    "x": 540,
    "y": 1000
  },
  "duration_ms": 500,
  "distance": 1000,
  "direction": "up",
  "execution_time": 520
}
```

**Error Scenarios:**
- Coordinates outside screen bounds
- Invalid duration (too short/long)
- Screen locked or touch disabled
- Gesture interrupted

---

### swipe_direction

Perform a swipe gesture in a specified cardinal direction with automatic coordinate calculation.

**Parameters:**
```json
{
  "direction": string,        // Required: "up", "down", "left", "right"
  "distance": number | null,  // Optional: Distance in pixels (auto-calculated if null)
  "duration_ms": number       // Default: 300 - Swipe duration in milliseconds
}
```

**Parameter Details:**
- `direction`: Cardinal direction for swipe (case-insensitive)
- `distance`: Swipe distance in pixels. If null, uses screen-appropriate default (typically 30-50% of screen dimension)
- `duration_ms`: Animation duration (100-2000ms recommended)

**Response Format:**
```json
{
  "success": boolean,
  "action": "swipe_direction",
  "direction": string,
  "calculated_coordinates": {
    "start_x": number,
    "start_y": number,
    "end_x": number,
    "end_y": number
  },
  "distance": number,
  "duration_ms": number,
  "execution_time": number,
  "screen_size": object
}
```

**Usage Examples:**
```json
// Swipe up with auto-distance
{
  "tool": "swipe_direction",
  "parameters": {
    "direction": "up"
  }
}

// Swipe right with specific distance
{
  "tool": "swipe_direction",
  "parameters": {
    "direction": "right",
    "distance": 600,
    "duration_ms": 400
  }
}

// Slow swipe down
{
  "tool": "swipe_direction",
  "parameters": {
    "direction": "down",
    "duration_ms": 800
  }
}

// Response example
{
  "success": true,
  "action": "swipe_direction",
  "direction": "up",
  "calculated_coordinates": {
    "start_x": 540,
    "start_y": 1600,
    "end_x": 540,
    "end_y": 800
  },
  "distance": 800,
  "duration_ms": 300,
  "execution_time": 320,
  "screen_size": {
    "width": 1080,
    "height": 2280
  }
}
```

**Error Scenarios:**
- Invalid direction parameter
- Distance exceeds screen dimensions
- Screen locked or gestures disabled

---

### input_text

Input text into the currently focused text field or input element.

**Parameters:**
```json
{
  "text": string,               // Required: Text to input
  "clear_existing": boolean    // Default: false - Clear existing text first
}
```

**Parameter Details:**
- `text`: Text content to input (supports Unicode, emojis, special characters)
- `clear_existing`: When true, clears field content before inputting new text

**Response Format:**
```json
{
  "success": boolean,
  "action": "input_text",
  "text_input": string,
  "cleared_existing": boolean,
  "focused_element": {          // Information about the focused input field
    "class": string,
    "resource_id": string,
    "text": string,
    "bounds": object
  },
  "execution_time": number
}
```

**Usage Examples:**
```json
// Input username
{
  "tool": "input_text",
  "parameters": {
    "text": "john.doe@example.com"
  }
}

// Replace existing text
{
  "tool": "input_text",
  "parameters": {
    "text": "New password123!",
    "clear_existing": true
  }
}

// Input with special characters
{
  "tool": "input_text",
  "parameters": {
    "text": "Hello 👋 World! @#$%"
  }
}

// Response example
{
  "success": true,
  "action": "input_text",
  "text_input": "john.doe@example.com",
  "cleared_existing": false,
  "focused_element": {
    "class": "android.widget.EditText",
    "resource_id": "com.example.app:id/username_field",
    "text": "john.doe@example.com",
    "bounds": {
      "left": 100,
      "top": 300,
      "right": 900,
      "bottom": 350
    }
  },
  "execution_time": 85
}
```

**Error Scenarios:**
- No text field currently focused
- Input method not available
- Text contains unsupported characters
- Field is read-only or disabled

---

### press_key

Press a device hardware or software key.

**Parameters:**
```json
{
  "keycode": string    // Required: Key code or name
}
```

**Parameter Details:**
- `keycode`: Android key code name or number. Common values:
  - Navigation: `BACK`, `HOME`, `RECENT_APPS`, `MENU`
  - Input: `ENTER`, `DELETE`, `SPACE`, `TAB`
  - Volume: `VOLUME_UP`, `VOLUME_DOWN`, `MUTE`
  - Media: `MEDIA_PLAY_PAUSE`, `MEDIA_NEXT`, `MEDIA_PREVIOUS`
  - Numbers: `0`-`9`, Letters: `A`-`Z`
  - Function: `POWER`, `CAMERA`, `SEARCH`

**Response Format:**
```json
{
  "success": boolean,
  "action": "press_key",
  "keycode": string,
  "key_name": string,      // Human-readable key name
  "execution_time": number
}
```

**Usage Examples:**
```json
// Go back
{
  "tool": "press_key",
  "parameters": {
    "keycode": "BACK"
  }
}

// Go to home screen
{
  "tool": "press_key",
  "parameters": {
    "keycode": "HOME"
  }
}

// Press Enter/Return
{
  "tool": "press_key",
  "parameters": {
    "keycode": "ENTER"
  }
}

// Volume up
{
  "tool": "press_key",
  "parameters": {
    "keycode": "VOLUME_UP"
  }
}

// Response example
{
  "success": true,
  "action": "press_key",
  "keycode": "BACK",
  "key_name": "Back Button",
  "execution_time": 25
}
```

**Error Scenarios:**
- Invalid or unsupported key code
- Hardware key not available on device
- Key blocked by current app or system
- Device not responding to input

---

## Media Capture

Tools for capturing screenshots and recording screen video.

### take_screenshot

Capture a screenshot of the current device screen.

**Parameters:**
```json
{
  "filename": string | null,      // Optional: Custom filename
  "pull_to_local": boolean        // Default: true - Download to local machine
}
```

**Parameter Details:**
- `filename`: Custom filename without extension (PNG added automatically). If null, generates timestamp-based name
- `pull_to_local`: When true, downloads screenshot to local machine. When false, keeps only on device

**Response Format:**
```json
{
  "success": boolean,
  "action": "take_screenshot",
  "screenshot": {
    "filename": string,         // Generated or custom filename
    "device_path": string,      // Path on Android device
    "local_path": string,       // Path on local machine (if pulled)
    "file_size": number,        // File size in bytes
    "dimensions": {
      "width": number,          // Image width in pixels
      "height": number          // Image height in pixels
    },
    "format": "PNG",
    "timestamp": string         // ISO timestamp of capture
  },
  "execution_time": number
}
```

**Usage Examples:**
```json
// Basic screenshot
{
  "tool": "take_screenshot",
  "parameters": {}
}

// Custom filename
{
  "tool": "take_screenshot",
  "parameters": {
    "filename": "login_screen"
  }
}

// Keep on device only
{
  "tool": "take_screenshot",
  "parameters": {
    "filename": "debug_capture",
    "pull_to_local": false
  }
}

// Response example
{
  "success": true,
  "action": "take_screenshot",
  "screenshot": {
    "filename": "screenshot_20240924_143022.png",
    "device_path": "/sdcard/screenshot_20240924_143022.png",
    "local_path": "./screenshots/screenshot_20240924_143022.png",
    "file_size": 245760,
    "dimensions": {
      "width": 1080,
      "height": 2280
    },
    "format": "PNG",
    "timestamp": "2024-09-24T14:30:22.456Z"
  },
  "execution_time": 180
}
```

**Error Scenarios:**
- Insufficient storage space
- Permission denied for file operations
- Screenshot service not available
- Screen content blocked (DRM/secure content)

---

### start_screen_recording

Start a screen recording session with customizable quality settings.

**Parameters:**
```json
{
  "filename": string | null,      // Optional: Custom filename
  "time_limit": number,           // Default: 180 - Recording time limit in seconds
  "bit_rate": string | null,      // Optional: Video bit rate (e.g., "4M", "8M")
  "size_limit": string | null     // Optional: Resolution limit (e.g., "720x1280")
}
```

**Parameter Details:**
- `filename`: Custom filename without extension (MP4 added automatically). If null, generates timestamp-based name
- `time_limit`: Maximum recording duration in seconds (1-180 typical range)
- `bit_rate`: Video quality in bits per second. Examples: "2M", "4M", "8M", "20M"
- `size_limit`: Resolution constraint. Examples: "720x1280", "1080x1920", "480x854"

**Response Format:**
```json
{
  "success": boolean,
  "action": "start_recording",
  "recording": {
    "recording_id": string,     // Unique identifier for this recording
    "filename": string,         // Generated or custom filename
    "device_path": string,      // Path on Android device
    "settings": {
      "time_limit": number,
      "bit_rate": string,
      "size_limit": string,
      "format": "MP4"
    },
    "start_time": string,       // ISO timestamp of recording start
    "status": "recording"
  },
  "execution_time": number
}
```

**Usage Examples:**
```json
// Basic recording
{
  "tool": "start_screen_recording",
  "parameters": {}
}

// High quality recording
{
  "tool": "start_screen_recording",
  "parameters": {
    "filename": "demo_video",
    "time_limit": 300,
    "bit_rate": "8M"
  }
}

// Compact recording for upload
{
  "tool": "start_screen_recording",
  "parameters": {
    "filename": "quick_demo",
    "time_limit": 60,
    "bit_rate": "2M",
    "size_limit": "720x1280"
  }
}

// Response example
{
  "success": true,
  "action": "start_recording",
  "recording": {
    "recording_id": "rec_20240924_143156_001",
    "filename": "demo_video.mp4",
    "device_path": "/sdcard/demo_video.mp4",
    "settings": {
      "time_limit": 300,
      "bit_rate": "8M",
      "size_limit": null,
      "format": "MP4"
    },
    "start_time": "2024-09-24T14:31:56.123Z",
    "status": "recording"
  },
  "execution_time": 95
}
```

**Error Scenarios:**
- Screen recording not supported on device
- Insufficient storage space
- Another recording already in progress
- Invalid bit rate or resolution settings

---

### stop_screen_recording

Stop an active screen recording session and optionally download the video.

**Parameters:**
```json
{
  "recording_id": string | null,  // Optional: Specific recording to stop
  "pull_to_local": boolean        // Default: true - Download to local machine
}
```

**Parameter Details:**
- `recording_id`: Identifier from `start_screen_recording` response. If null, stops all active recordings
- `pull_to_local`: When true, downloads video file to local machine

**Response Format:**
```json
{
  "success": boolean,
  "action": "stop_recording",
  "recording": {
    "recording_id": string,
    "filename": string,
    "device_path": string,
    "local_path": string,       // If pulled to local
    "file_size": number,        // Final file size in bytes
    "duration": number,         // Actual recording duration in seconds
    "settings": object,
    "start_time": string,
    "end_time": string,         // ISO timestamp of recording end
    "status": "completed"
  },
  "execution_time": number
}
```

**Usage Examples:**
```json
// Stop all recordings
{
  "tool": "stop_screen_recording",
  "parameters": {}
}

// Stop specific recording
{
  "tool": "stop_screen_recording",
  "parameters": {
    "recording_id": "rec_20240924_143156_001"
  }
}

// Stop and keep on device
{
  "tool": "stop_screen_recording",
  "parameters": {
    "recording_id": "rec_20240924_143156_001",
    "pull_to_local": false
  }
}

// Response example
{
  "success": true,
  "action": "stop_recording",
  "recording": {
    "recording_id": "rec_20240924_143156_001",
    "filename": "demo_video.mp4",
    "device_path": "/sdcard/demo_video.mp4",
    "local_path": "./recordings/demo_video.mp4",
    "file_size": 12845760,
    "duration": 45.3,
    "settings": {
      "time_limit": 300,
      "bit_rate": "8M",
      "size_limit": null,
      "format": "MP4"
    },
    "start_time": "2024-09-24T14:31:56.123Z",
    "end_time": "2024-09-24T14:32:41.456Z",
    "status": "completed"
  },
  "execution_time": 220
}
```

**Error Scenarios:**
- No active recordings to stop
- Specified recording ID not found
- File transfer failed
- Recording corrupted or incomplete

---

### list_active_recordings

List all currently active screen recording sessions.

**Parameters:** None

**Response Format:**
```json
{
  "success": boolean,
  "active_recordings": [
    {
      "recording_id": string,
      "filename": string,
      "device_path": string,
      "settings": object,
      "start_time": string,
      "elapsed_time": number,     // Seconds since recording started
      "estimated_size": number,   // Estimated file size so far
      "status": "recording"
    }
  ],
  "count": number
}
```

**Usage Example:**
```json
// Request
{
  "tool": "list_active_recordings",
  "parameters": {}
}

// Response
{
  "success": true,
  "active_recordings": [
    {
      "recording_id": "rec_20240924_143156_001",
      "filename": "demo_video.mp4",
      "device_path": "/sdcard/demo_video.mp4",
      "settings": {
        "time_limit": 300,
        "bit_rate": "8M",
        "size_limit": null,
        "format": "MP4"
      },
      "start_time": "2024-09-24T14:31:56.123Z",
      "elapsed_time": 127.5,
      "estimated_size": 8456000,
      "status": "recording"
    }
  ],
  "count": 1
}
```

**Error Scenarios:**
- Unable to query recording status
- Recording service not available

---

## Log Monitoring

Tools for monitoring and analyzing device logs for debugging and troubleshooting.

### get_logcat

Retrieve device logs with filtering options for analysis and debugging.

**Parameters:**
```json
{
  "tag_filter": string | null,    // Optional: Filter by log tag
  "priority": string,             // Default: "V" - Minimum log priority level
  "max_lines": number,            // Default: 100 - Maximum lines to return
  "clear_first": boolean          // Default: false - Clear logcat buffer first
}
```

**Parameter Details:**
- `tag_filter`: Filter logs to specific tag (e.g., "ActivityManager", "MyApp")
- `priority`: Minimum log level to include:
  - `V`: Verbose (all logs)
  - `D`: Debug and above
  - `I`: Info and above
  - `W`: Warning and above
  - `E`: Error and above
  - `F`: Fatal only
  - `S`: Silent (none)
- `max_lines`: Maximum number of log entries to return (1-10000 range)
- `clear_first`: Clear existing log buffer before reading (useful for capturing fresh logs)

**Response Format:**
```json
{
  "success": boolean,
  "logs": [
    {
      "timestamp": string,        // Log entry timestamp
      "priority": string,         // Log priority (V/D/I/W/E/F)
      "tag": string,              // Log tag/source
      "pid": number,              // Process ID
      "tid": number,              // Thread ID
      "message": string           // Log message content
    }
  ],
  "total_lines": number,          // Total log entries found
  "returned_lines": number,       // Number of entries returned (limited by max_lines)
  "filter_criteria": {
    "tag_filter": string,
    "priority": string,
    "max_lines": number,
    "clear_first": boolean
  },
  "execution_time": number
}
```

**Usage Examples:**
```json
// Get recent error logs
{
  "tool": "get_logcat",
  "parameters": {
    "priority": "E",
    "max_lines": 50
  }
}

// Monitor specific app
{
  "tool": "get_logcat",
  "parameters": {
    "tag_filter": "MyApp",
    "priority": "D",
    "max_lines": 200
  }
}

// Fresh system logs
{
  "tool": "get_logcat",
  "parameters": {
    "clear_first": true,
    "priority": "I",
    "max_lines": 100
  }
}

// Response example
{
  "success": true,
  "logs": [
    {
      "timestamp": "2024-09-24 14:35:22.123",
      "priority": "E",
      "tag": "AndroidRuntime",
      "pid": 12345,
      "tid": 12345,
      "message": "FATAL EXCEPTION: main\nProcess: com.example.app, PID: 12345\njava.lang.NullPointerException: Attempt to invoke virtual method..."
    },
    {
      "timestamp": "2024-09-24 14:35:20.456",
      "priority": "W",
      "tag": "ActivityManager",
      "pid": 1234,
      "tid": 1456,
      "message": "Activity pause timeout for ActivityRecord{abc123 u0 com.example.app/.MainActivity t456}"
    }
  ],
  "total_lines": 1247,
  "returned_lines": 2,
  "filter_criteria": {
    "tag_filter": null,
    "priority": "E",
    "max_lines": 50,
    "clear_first": false
  },
  "execution_time": 85
}
```

**Error Scenarios:**
- Logcat service not available
- Permission denied for log access
- Invalid priority level
- Buffer clear failed

---

### start_log_monitoring

Start continuous monitoring of device logs with real-time filtering and optional file output.

**Parameters:**
```json
{
  "tag_filter": string | null,    // Optional: Filter by log tag
  "priority": string,             // Default: "I" - Minimum log priority level
  "output_file": string | null    // Optional: Save logs to file
}
```

**Parameter Details:**
- `tag_filter`: Monitor logs from specific tag only
- `priority`: Minimum log level to capture (same values as get_logcat)
- `output_file`: Local filename to save monitored logs. If null, logs stored in memory only

**Response Format:**
```json
{
  "success": boolean,
  "monitor": {
    "monitor_id": string,       // Unique identifier for this monitor session
    "tag_filter": string,
    "priority": string,
    "output_file": string,
    "start_time": string,       // ISO timestamp when monitoring started
    "status": "monitoring",
    "logs_captured": number     // Initial count (usually 0)
  },
  "execution_time": number
}
```

**Usage Examples:**
```json
// Monitor app crashes
{
  "tool": "start_log_monitoring",
  "parameters": {
    "tag_filter": "AndroidRuntime",
    "priority": "E",
    "output_file": "crash_logs.txt"
  }
}

// General system monitoring
{
  "tool": "start_log_monitoring",
  "parameters": {
    "priority": "W"
  }
}

// Monitor specific app with file output
{
  "tool": "start_log_monitoring",
  "parameters": {
    "tag_filter": "MyApp",
    "priority": "D",
    "output_file": "myapp_debug.log"
  }
}

// Response example
{
  "success": true,
  "monitor": {
    "monitor_id": "monitor_20240924_143645_001",
    "tag_filter": "AndroidRuntime",
    "priority": "E",
    "output_file": "crash_logs.txt",
    "start_time": "2024-09-24T14:36:45.789Z",
    "status": "monitoring",
    "logs_captured": 0
  },
  "execution_time": 65
}
```

**Error Scenarios:**
- Unable to start log monitoring service
- File output location not accessible
- Too many concurrent monitors
- Permission denied for log access

---

### stop_log_monitoring

Stop an active log monitoring session and retrieve captured logs.

**Parameters:**
```json
{
  "monitor_id": string | null    // Optional: Specific monitor to stop
}
```

**Parameter Details:**
- `monitor_id`: Identifier from `start_log_monitoring` response. If null, stops all active monitors

**Response Format:**
```json
{
  "success": boolean,
  "monitor": {
    "monitor_id": string,
    "tag_filter": string,
    "priority": string,
    "output_file": string,
    "start_time": string,
    "end_time": string,         // ISO timestamp when monitoring stopped
    "duration": number,         // Monitoring duration in seconds
    "logs_captured": number,    // Total number of log entries captured
    "status": "stopped"
  },
  "captured_logs": [             // Recent logs captured (last 100 entries)
    {
      "timestamp": string,
      "priority": string,
      "tag": string,
      "pid": number,
      "tid": number,
      "message": string
    }
  ],
  "execution_time": number
}
```

**Usage Examples:**
```json
// Stop all monitors
{
  "tool": "stop_log_monitoring",
  "parameters": {}
}

// Stop specific monitor
{
  "tool": "stop_log_monitoring",
  "parameters": {
    "monitor_id": "monitor_20240924_143645_001"
  }
}

// Response example
{
  "success": true,
  "monitor": {
    "monitor_id": "monitor_20240924_143645_001",
    "tag_filter": "AndroidRuntime",
    "priority": "E",
    "output_file": "crash_logs.txt",
    "start_time": "2024-09-24T14:36:45.789Z",
    "end_time": "2024-09-24T14:42:15.234Z",
    "duration": 329.445,
    "logs_captured": 3,
    "status": "stopped"
  },
  "captured_logs": [
    {
      "timestamp": "2024-09-24 14:38:22.123",
      "priority": "E",
      "tag": "AndroidRuntime",
      "pid": 12345,
      "tid": 12345,
      "message": "FATAL EXCEPTION: main\nProcess: com.example.testapp, PID: 12345\njava.lang.IllegalStateException..."
    }
  ],
  "execution_time": 45
}
```

**Error Scenarios:**
- Monitor ID not found
- Monitor already stopped
- Unable to retrieve captured logs

---

### list_active_monitors

List all active log monitoring sessions and their current status.

**Parameters:** None

**Response Format:**
```json
{
  "success": boolean,
  "active_monitors": [
    {
      "monitor_id": string,
      "tag_filter": string,
      "priority": string,
      "output_file": string,
      "start_time": string,
      "elapsed_time": number,     // Seconds since monitoring started
      "logs_captured": number,    // Number of logs captured so far
      "status": "monitoring"
    }
  ],
  "count": number
}
```

**Usage Example:**
```json
// Request
{
  "tool": "list_active_monitors",
  "parameters": {}
}

// Response
{
  "success": true,
  "active_monitors": [
    {
      "monitor_id": "monitor_20240924_143645_001",
      "tag_filter": "AndroidRuntime",
      "priority": "E",
      "output_file": "crash_logs.txt",
      "start_time": "2024-09-24T14:36:45.789Z",
      "elapsed_time": 125.5,
      "logs_captured": 1,
      "status": "monitoring"
    },
    {
      "monitor_id": "monitor_20240924_143720_002",
      "tag_filter": null,
      "priority": "W",
      "output_file": null,
      "start_time": "2024-09-24T14:37:20.123Z",
      "elapsed_time": 90.2,
      "logs_captured": 47,
      "status": "monitoring"
    }
  ],
  "count": 2
}
```

**Error Scenarios:**
- Unable to query monitor status
- Log monitoring service not available

---

## Common Usage Patterns

### Device Setup and Testing Workflow

```json
// 1. Connect to device
{
  "tool": "get_devices",
  "parameters": {}
}

// 2. Select device and check health
{
  "tool": "select_device",
  "parameters": {
    "device_id": "emulator-5554"
  }
}

// 3. Get device information
{
  "tool": "get_device_info",
  "parameters": {}
}

// 4. Take initial screenshot
{
  "tool": "take_screenshot",
  "parameters": {
    "filename": "initial_state"
  }
}
```

### UI Automation Workflow

```json
// 1. Get current UI layout
{
  "tool": "get_ui_layout",
  "parameters": {
    "compressed": true
  }
}

// 2. Find login button
{
  "tool": "find_elements",
  "parameters": {
    "text": "Login",
    "clickable_only": true
  }
}

// 3. Tap the login button
{
  "tool": "tap_element",
  "parameters": {
    "text": "Login"
  }
}

// 4. Input username
{
  "tool": "tap_element",
  "parameters": {
    "resource_id": "com.app:id/username"
  }
}

{
  "tool": "input_text",
  "parameters": {
    "text": "testuser@example.com",
    "clear_existing": true
  }
}

// 5. Input password
{
  "tool": "tap_element",
  "parameters": {
    "resource_id": "com.app:id/password"
  }
}

{
  "tool": "input_text",
  "parameters": {
    "text": "secretpassword"
  }
}

// 6. Submit form
{
  "tool": "press_key",
  "parameters": {
    "keycode": "ENTER"
  }
}
```

### Testing and Debugging Workflow

```json
// 1. Start log monitoring
{
  "tool": "start_log_monitoring",
  "parameters": {
    "priority": "W",
    "output_file": "test_logs.txt"
  }
}

// 2. Start screen recording
{
  "tool": "start_screen_recording",
  "parameters": {
    "filename": "test_session",
    "time_limit": 300
  }
}

// 3. Perform test actions
// ... (various interactions) ...

// 4. Capture final state
{
  "tool": "take_screenshot",
  "parameters": {
    "filename": "final_state"
  }
}

// 5. Stop recording and monitoring
{
  "tool": "stop_screen_recording",
  "parameters": {}
}

{
  "tool": "stop_log_monitoring",
  "parameters": {}
}
```

### Error Recovery Patterns

```json
// If element not found, get UI layout and search again
{
  "tool": "tap_element",
  "parameters": {
    "text": "Submit"
  }
}
// If fails, follow up with:
{
  "tool": "get_ui_layout",
  "parameters": {}
}

{
  "tool": "find_elements",
  "parameters": {
    "text": "Submit",
    "exact_match": false
  }
}

// If still not found, try alternative selectors
{
  "tool": "find_elements",
  "parameters": {
    "class_name": "android.widget.Button",
    "clickable_only": true
  }
}
```

### Performance Testing Pattern

```json
// 1. Clear logs and start fresh monitoring
{
  "tool": "get_logcat",
  "parameters": {
    "clear_first": true,
    "max_lines": 1
  }
}

{
  "tool": "start_log_monitoring",
  "parameters": {
    "tag_filter": "ActivityManager",
    "priority": "I"
  }
}

// 2. Perform performance-critical operations
// ... (app navigation, data loading, etc.) ...

// 3. Stop monitoring and analyze logs
{
  "tool": "stop_log_monitoring",
  "parameters": {}
}
```

---

This API reference provides comprehensive documentation for all Android MCP Server tools with detailed parameter descriptions, response formats, usage examples, and error scenarios. The tools enable complete Android device automation for testing, debugging, and interaction workflows.