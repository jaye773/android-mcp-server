# Android MCP Server — Tool Reference

This document lists the MCP tools exposed by the Android MCP Server, including the expected parameters and example responses. Values in examples are illustrative.

- Transport: JSON-RPC over stdio (FastMCP)
- Runtime: Python 3.11, async
- Key modules: `src/server.py`, `src/adb_manager.py`, `src/ui_inspector.py`, `src/screen_interactor.py`, `src/media_capture.py`, `src/log_monitor.py`

---

## Device Management

### get_devices
- Parameters: none
- Example response:
```json
{
  "success": true,
  "devices": [
    { "id": "R58M12ABCD", "status": "device", "model": "SM-G991U", "product": "o1q", "device": "o1q" },
    { "id": "emulator-5554", "status": "device", "model": "sdk_gphone64_x86_64" }
  ],
  "count": 2
}
```

### select_device
- Parameters:
  - `device_id`: string | null (optional; when omitted, auto-selects)
- Example response (explicit selection):
```json
{ "success": true, "selected_device": "R58M12ABCD", "health": { "success": true, "healthy": true, "checks": { "connectivity": {"passed": true, "details": "connected"} }, "device_id": "R58M12ABCD" } }
```
- Example response (auto-select):
```json
{ "success": true, "selected": { "id": "R58M12ABCD", "status": "device" }, "reason": "first_physical" }
```

### get_device_info
- Parameters: none
- Example response:
```json
{
  "success": true,
  "device_info": {
    "device_id": "R58M12ABCD",
    "model": "Pixel 7",
    "manufacturer": "Google",
    "android_version": "14",
    "api_level": "34",
    "serial": "R58M12ABCD"
  },
  "screen_size": { "success": true, "width": 1080, "height": 2400, "raw_output": "Physical size: 1080x2400" },
  "health": { "success": true, "healthy": true, "checks": { /* ... */ }, "device_id": "R58M12ABCD" }
}
```

---

## UI Layout and Inspection

### get_ui_layout
- Parameters:
  - `compressed`: boolean = true (use `uiautomator --compressed`)
  - `include_invisible`: boolean = false (include nodes with displayed=false)
- Example response:
```json
{
  "success": true,
  "elements": [
    {
      "class_name": "android.widget.TextView",
      "resource_id": "com.example:id/title",
      "text": "Welcome",
      "content_desc": null,
      "bounds": { "left": 48, "top": 128, "right": 1032, "bottom": 208 },
      "center": { "x": 540, "y": 168 },
      "clickable": false,
      "enabled": true,
      "focusable": false,
      "scrollable": false,
      "displayed": true,
      "xpath": "/hierarchy[0]/node[0]",
      "index": 0,
      "children_count": 0
    }
  ],
  "xml_dump": "<hierarchy>...</hierarchy>",
  "stats": { "total_elements": 142, "clickable_elements": 37 }
}
```

### find_elements
- Parameters:
  - `text`: string | null
  - `resource_id`: string | null
  - `content_desc`: string | null
  - `class_name`: string | null
  - `clickable_only`: boolean = false
  - `enabled_only`: boolean = true
  - `exact_match`: boolean = false
- Example response:
```json
{
  "success": true,
  "elements": [ /* element dicts as above */ ],
  "count": 3,
  "search_criteria": {
    "text": "Sign in",
    "resource_id": null,
    "content_desc": null,
    "class_name": null,
    "clickable_only": true,
    "enabled_only": true,
    "exact_match": false
  }
}
```

---

## Screen Interaction

### tap_screen
- Parameters:
  - `x`: integer (pixels)
  - `y`: integer (pixels)
- Example response:
```json
{ "success": true, "action": "tap", "coordinates": { "x": 540, "y": 168 }, "details": "Tap executed" }
```

### tap_element
- Parameters:
  - `text`: string | null
  - `resource_id`: string | null
  - `content_desc`: string | null
  - `index`: integer = 0 (choose among multiple matches)
- Example response:
```json
{
  "success": true,
  "action": "tap",
  "coordinates": { "x": 540, "y": 168 },
  "element": { /* element dict */ },
  "index_used": 0,
  "total_found": 2,
  "details": "Tap executed"
}
```

### swipe_screen
- Parameters:
  - `start_x`: integer
  - `start_y`: integer
  - `end_x`: integer
  - `end_y`: integer
  - `duration_ms`: integer = 300
- Example response:
```json
{
  "success": true,
  "action": "swipe",
  "start": { "x": 540, "y": 1600 },
  "end": { "x": 540, "y": 800 },
  "duration_ms": 300,
  "details": "Swipe executed"
}
```

### swipe_direction
- Parameters:
  - `direction`: "up" | "down" | "left" | "right"
  - `distance`: integer | null (default: min(width,height)/3)
  - `duration_ms`: integer = 300
- Example response:
```json
{
  "success": true,
  "action": "swipe",
  "start": { "x": 540, "y": 1200 },
  "end": { "x": 540, "y": 600 },
  "duration_ms": 300,
  "details": "Swipe executed",
  "direction": "up",
  "distance": 600,
  "screen_size": { "width": 1080, "height": 2400 }
}
```

### input_text
- Parameters:
  - `text`: string
  - `clear_existing`: boolean = false
- Example response:
```json
{ "success": true, "action": "text_input", "text": "hello world", "cleared_first": false, "details": "Text input successful" }
```

### press_key
- Parameters:
  - `keycode`: string (e.g., "BACK", "HOME", "ENTER" or "KEYCODE_BACK")
- Example response:
```json
{ "success": true, "action": "key_press", "keycode": "KEYCODE_BACK", "original_input": "BACK", "details": "Key KEYCODE_BACK pressed" }
```

---

## Media Capture

### take_screenshot
- Parameters:
  - `filename`: string | null (auto-generated if null)
  - `pull_to_local`: boolean = true
- Example response:
```json
{
  "success": true,
  "action": "screenshot",
  "filename": "screenshot_20240901_121314.png",
  "device_path": "/sdcard/screenshot_20240901_121314.png",
  "format": "png",
  "local_path": "assets/screenshot_20240901_121314.png",
  "file_size_bytes": 523456,
  "file_size_mb": 0.5
}
```

### start_screen_recording
- Parameters:
  - `filename`: string | null (auto-suffixed .mp4 if missing)
  - `time_limit`: integer = 180
  - `bit_rate`: string | null (e.g., "4M")
  - `size_limit`: string | null (e.g., "720x1280")
- Example response:
```json
{
  "success": true,
  "action": "start_recording",
  "recording_id": "R58M12ABCD_recording_20240901_121314.mp4",
  "filename": "recording_20240901_121314.mp4",
  "device_path": "/sdcard/recording_20240901_121314.mp4",
  "time_limit": 180,
  "bit_rate": null,
  "size_limit": null,
  "process_id": 12345
}
```

### stop_screen_recording
- Parameters:
  - `recording_id`: string | null (when null, stops all)
  - `pull_to_local`: boolean = true
- Example response (single):
```json
{
  "success": true,
  "action": "stop_recording",
  "recording_id": "R58M12ABCD_recording_20240901_121314.mp4",
  "filename": "recording_20240901_121314.mp4",
  "duration_seconds": 42.2,
  "device_path": "/sdcard/recording_20240901_121314.mp4",
  "local_path": "assets/recording_20240901_121314.mp4",
  "file_size_bytes": 12582912,
  "file_size_mb": 12.0
}
```

### list_active_recordings
- Parameters: none
- Example response:
```json
{
  "success": true,
  "active_recordings": [
    {
      "recording_id": "R58M12ABCD_recording_20240901_121314.mp4",
      "filename": "recording_20240901_121314.mp4",
      "duration_seconds": 15.8,
      "time_limit": 180,
      "device_path": "/sdcard/recording_20240901_121314.mp4"
    }
  ],
  "count": 1
}
```

---

## Log Monitoring

### get_logcat
- Parameters:
  - `tag_filter`: string | null
  - `priority`: "V" | "D" | "I" | "W" | "E" | "F" | "S" = "V"
  - `max_lines`: integer = 100
  - `clear_first`: boolean = false
- Example response:
```json
{
  "success": true,
  "action": "get_logcat",
  "entries_count": 3,
  "entries": [
    {
      "timestamp": "2024-09-01T12:13:14.123000",
      "level": "I",
      "tag": "ActivityManager",
      "pid": 1234,
      "tid": 1234,
      "message": "Displayed com.example/.MainActivity"
    }
  ],
  "filter_applied": { "tag": "ActivityManager", "priority": "I", "max_lines": 100, "since_time": null }
}
```

### start_log_monitoring
- Parameters:
  - `tag_filter`: string | null
  - `priority`: "V" | "D" | "I" | "W" | "E" | "F" | "S" = "I"
  - `output_file`: string | null (".log" added if missing)
- Example response:
```json
{
  "success": true,
  "action": "start_log_monitoring",
  "monitor_id": "logmon_R58M12ABCD_20240901_121314",
  "tag_filter": null,
  "priority": "I",
  "output_file": "logs/session_20240901_121314.log",
  "process_id": 23456
}
```

### stop_log_monitoring
- Parameters:
  - `monitor_id`: string | null (when null, stops all)
- Example response (single):
```json
{
  "success": true,
  "action": "stop_monitoring",
  "monitor_id": "logmon_R58M12ABCD_20240901_121314",
  "duration_seconds": 62.4,
  "entries_processed": 452,
  "output_file": "logs/session_20240901_121314.log"
}
```

### list_active_monitors
- Parameters: none
- Example response:
```json
{
  "success": true,
  "active_monitors": [
    {
      "monitor_id": "logmon_R58M12ABCD_20240901_121314",
      "duration_seconds": 62.4,
      "tag_filter": null,
      "priority": "I",
      "entries_processed": 452,
      "output_file": "logs/session_20240901_121314.log"
    }
  ],
  "count": 1
}
```

---

## Notes
- On success, many actions include human-readable `details`; on failure, errors are provided via `error` or stderr-captured `details`.
- Some responses include additional fields based on operation mode (e.g., local file info only when `pull_to_local` is true).
- Device-specific values (screen size, model, tags) vary by hardware/emulator and OS.
