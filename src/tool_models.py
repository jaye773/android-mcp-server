"""Pydantic models for MCP tool parameters."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DeviceSelectionParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"device_id": "emulator-5554"},
                {"device_id": "DA1A2BC3DEF4"},
                {"device_id": None},
            ]
        }
    )
    device_id: Optional[str] = Field(
        default=None, description="Specific device ID to select"
    )


class UILayoutParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"compressed": True, "include_invisible": False},
                {"compressed": False, "include_invisible": True},
            ]
        }
    )
    compressed: bool = Field(default=True, description="Use compressed UI dump")
    include_invisible: bool = Field(
        default=False, description="Include invisible elements"
    )


class ElementSearchParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"text": "Settings", "clickable_only": True},
                {
                    "resource_id": "com.app:id/login_button",
                    "enabled_only": True,
                    "exact_match": True,
                },
                {"content_desc": "Submit", "class_name": "android.widget.Button"},
            ]
        }
    )
    text: Optional[str] = Field(default=None, description="Text content to search for")
    resource_id: Optional[str] = Field(default=None, description="Resource ID to match")
    content_desc: Optional[str] = Field(
        default=None, description="Content description to match"
    )
    class_name: Optional[str] = Field(default=None, description="Class name to match")
    clickable_only: bool = Field(
        default=False, description="Only return clickable elements"
    )
    enabled_only: bool = Field(default=True, description="Only return enabled elements")
    exact_match: bool = Field(default=False, description="Use exact string matching")


class TapCoordinatesParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"x": 540, "y": 1600},
                {"x": 100, "y": 300},
            ]
        }
    )
    x: int = Field(description="X coordinate")
    y: int = Field(description="Y coordinate")


class TapElementParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"text": "Login", "index": 0},
                {"resource_id": "com.app:id/submit", "index": 0},
                {"content_desc": "Navigate up", "index": 0},
            ]
        }
    )
    text: Optional[str] = Field(default=None, description="Text to find and tap")
    resource_id: Optional[str] = Field(
        default=None, description="Resource ID to find and tap"
    )
    content_desc: Optional[str] = Field(
        default=None, description="Content description to find and tap"
    )
    index: int = Field(default=0, description="Index of element if multiple matches")
    clickable_only: bool = Field(
        default=False,
        description="Only find clickable elements (default: False for flexibility)",
    )
    enabled_only: bool = Field(
        default=False,
        description="Only find enabled elements (default: False for flexibility)",
    )


class SwipeParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "start_x": 540,
                    "start_y": 1600,
                    "end_x": 540,
                    "end_y": 600,
                    "duration_ms": 400,
                },
                {"start_x": 100, "start_y": 400, "end_x": 900, "end_y": 400},
            ]
        }
    )
    start_x: int = Field(description="Start X coordinate")
    start_y: int = Field(description="Start Y coordinate")
    end_x: int = Field(description="End X coordinate")
    end_y: int = Field(description="End Y coordinate")
    duration_ms: int = Field(default=300, description="Swipe duration in milliseconds")


class SwipeDirectionParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"direction": "up", "distance": 600, "duration_ms": 500},
                {"direction": "left"},
            ]
        }
    )
    direction: str = Field(description="Swipe direction: up, down, left, right")
    distance: Optional[int] = Field(
        default=None, description="Swipe distance in pixels"
    )
    duration_ms: int = Field(default=300, description="Swipe duration in milliseconds")


class TextInputParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"text": "hello world", "clear_existing": False},
                {"text": "user@example.com", "clear_existing": True},
            ]
        }
    )
    text: str = Field(description="Text to input")
    clear_existing: bool = Field(default=False, description="Clear existing text first")
    submit: bool = Field(
        default=False, description="Whether to submit the text by pressing Enter"
    )


class KeyPressParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"keycode": "BACK"},
                {"keycode": "ENTER"},
                {"keycode": "KEYCODE_VOLUME_UP"},
            ]
        }
    )
    keycode: str = Field(description="Key code or name (BACK, HOME, ENTER, etc.)")


class ScreenshotParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"filename": "before_action.png", "pull_to_local": True},
                {"pull_to_local": True},
            ]
        }
    )
    filename: Optional[str] = Field(default=None, description="Custom filename")
    pull_to_local: bool = Field(default=True, description="Download to local machine")


class RecordingParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "filename": "flow.mp4",
                    "time_limit": 120,
                    "bit_rate": "4M",
                    "size_limit": "720x1280",
                },
                {"time_limit": 60},
            ]
        }
    )
    filename: Optional[str] = Field(default=None, description="Custom filename")
    time_limit: int = Field(default=180, description="Recording time limit in seconds")
    bit_rate: Optional[str] = Field(
        default=None, description="Video bit rate (e.g., '4M')"
    )
    size_limit: Optional[str] = Field(
        default=None, description="Resolution limit (e.g., '720x1280')"
    )


class StopRecordingParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "recording_id": "emulator-5554_recording_20250101_101500.mp4",
                    "pull_to_local": True,
                },
                {"pull_to_local": True},
            ]
        }
    )
    recording_id: Optional[str] = Field(
        default=None, description="Specific recording to stop"
    )
    pull_to_local: bool = Field(default=True, description="Download to local machine")


class LogcatParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"tag_filter": "ActivityManager", "priority": "I", "max_lines": 200},
                {"priority": "E", "max_lines": 100, "clear_first": True},
            ]
        }
    )
    tag_filter: Optional[str] = Field(default=None, description="Filter by tag")
    priority: str = Field(
        default="V", description="Minimum log priority (V/D/I/W/E/F/S)"
    )
    max_lines: int = Field(default=100, description="Maximum lines to return")
    clear_first: bool = Field(default=False, description="Clear logcat buffer first")


class LogMonitorParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"tag_filter": "MyApp", "priority": "D", "output_file": "myapp.log"},
                {"priority": "I"},
            ]
        }
    )
    tag_filter: Optional[str] = Field(default=None, description="Filter by tag")
    priority: str = Field(default="I", description="Minimum log priority")
    output_file: Optional[str] = Field(default=None, description="Save to file")


class StopMonitorParams(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"monitor_id": "logmon_emulator-5554_20250101_101500"},
                {"monitor_id": None},
            ]
        }
    )
    monitor_id: Optional[str] = Field(
        default=None, description="Specific monitor to stop"
    )
