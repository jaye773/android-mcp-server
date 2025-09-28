"""Media capture capabilities for screenshots and video recording."""

from __future__ import annotations

import asyncio
import logging
import shlex
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, TypedDict

from .adb_manager import ADBManager
from .ui_inspector import UIElement

logger = logging.getLogger(__name__)


# Type definitions for better type safety
class ScreenshotResult(TypedDict, total=False):
    """Type definition for screenshot operation results."""

    success: bool
    action: str
    filename: str
    device_path: str
    format: str
    local_path: str
    file_size_bytes: int
    file_size_mb: float
    pull_failed: bool
    pull_error: str
    error: str
    details: str
    highlighted_path: str
    elements_highlighted: int
    highlight_warning: str
    highlight_error: str
    elements_to_highlight: int


class RecordingInfo(TypedDict):
    """Type definition for active recording session information."""

    process: asyncio.subprocess.Process
    filename: str
    device_path: str
    local_path: Path
    start_time: datetime
    time_limit: int
    options: str


class RecordingResult(TypedDict, total=False):
    """Type definition for recording operation results."""

    success: bool
    action: str
    recording_id: str
    filename: str
    device_path: str
    time_limit: int
    bit_rate: Optional[str]
    size_limit: Optional[str]
    process_id: Optional[int]
    duration_seconds: float
    local_path: str
    file_size_bytes: int
    file_size_mb: float
    pull_failed: bool
    pull_error: str
    error: str
    active_recordings: List[str]
    recordings_stopped: int
    results: List[Dict[str, Any]]
    cleaned_count: int


class ActiveRecordingInfo(TypedDict):
    """Type definition for active recording information in listings."""

    recording_id: str
    filename: str
    duration_seconds: float
    time_limit: int
    device_path: str


class MediaCapture:
    """Handle screenshot and video recording operations."""

    def __init__(self, adb_manager: ADBManager, output_dir: str = "./assets") -> None:
        self.adb_manager = adb_manager
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    async def take_screenshot(
        self,
        filename: Optional[str] = None,
        pull_to_local: bool = True,
        format: str = "png",
    ) -> ScreenshotResult:
        """
        Capture device screenshot.

        Args:
            filename: Custom filename (auto-generated if None)
            pull_to_local: Download to local machine
            format: Image format (png/jpg)
        """
        try:
            # Generate filename if not provided
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.{format}"

            # Ensure filename has correct extension
            if not filename.endswith(f".{format}"):
                filename = f"{filename}.{format}"

            device_path = f"/sdcard/{filename}"
            local_path = self.output_dir / filename

            # Capture screenshot on device
            capture_command = f"adb -s {{device}} shell screencap -p {device_path}"
            capture_result = await self.adb_manager.execute_adb_command(capture_command)

            if not capture_result["success"]:
                return {
                    "success": False,
                    "error": "Screenshot capture failed",
                    "details": capture_result.get("stderr", ""),
                }

            result: ScreenshotResult = {
                "success": True,
                "action": "screenshot",
                "filename": filename,
                "device_path": device_path,
                "format": format,
            }

            # Pull to local machine if requested
            if pull_to_local:
                pull_result = await self._pull_file_from_device(device_path, local_path)
                # Merge recognized fields without violating TypedDict typing
                if "local_path" in pull_result:
                    result["local_path"] = str(pull_result["local_path"])
                if "file_size_bytes" in pull_result:
                    result["file_size_bytes"] = int(pull_result["file_size_bytes"])
                if "file_size_mb" in pull_result:
                    result["file_size_mb"] = float(pull_result["file_size_mb"])
                if "pull_failed" in pull_result:
                    result["pull_failed"] = bool(pull_result["pull_failed"])
                if "pull_error" in pull_result:
                    result["pull_error"] = str(pull_result["pull_error"])

                # Clean up device file
                cleanup_command = f"adb -s {{device}} shell rm {device_path}"
                await self.adb_manager.execute_adb_command(cleanup_command)

            return result

        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return {"success": False, "error": f"Screenshot operation failed: {str(e)}"}

    async def take_screenshot_with_highlights(
        self, elements_to_highlight: List[UIElement], filename: Optional[str] = None
    ) -> ScreenshotResult:
        """Take screenshot and overlay element highlights."""
        try:
            # Take base screenshot
            screenshot_result = await self.take_screenshot(filename, pull_to_local=True)

            if not screenshot_result["success"]:
                return screenshot_result

            # Try to add highlights if PIL is available
            try:
                from PIL import Image, ImageDraw

                # Load screenshot
                local_path = Path(screenshot_result["local_path"])
                image = Image.open(local_path)
                draw = ImageDraw.Draw(image)

                # Draw highlights for each element
                for i, element in enumerate(elements_to_highlight):
                    bounds = element.bounds
                    # Draw rectangle around element
                    draw.rectangle(
                        [
                            bounds["left"],
                            bounds["top"],
                            bounds["right"],
                            bounds["bottom"],
                        ],
                        outline="red",
                        width=3,
                    )

                    # Add element number
                    draw.text(
                        (bounds["left"] + 5, bounds["top"] + 5), str(i + 1), fill="red"
                    )

                # Save highlighted version
                highlighted_path = local_path.with_suffix(
                    f"_highlighted{local_path.suffix}"
                )
                image.save(highlighted_path)

                screenshot_result.update(
                    {
                        "highlighted_path": str(highlighted_path),
                        "elements_highlighted": len(elements_to_highlight),
                    }
                )

            except ImportError:
                screenshot_result.update(
                    {
                        "highlight_warning": "PIL not available - highlights not added",
                        "elements_to_highlight": len(elements_to_highlight),
                    }
                )
            except Exception as e:
                screenshot_result.update(
                    {
                        "highlight_error": f"Highlighting failed: {str(e)}",
                        "elements_to_highlight": len(elements_to_highlight),
                    }
                )

            return screenshot_result

        except Exception as e:
            logger.error(f"Screenshot with highlights failed: {e}")
            return {
                "success": False,
                "error": f"Screenshot with highlights failed: {str(e)}",
            }

    async def _pull_file_from_device(
        self, device_path: str, local_path: Path
    ) -> Dict[str, Union[str, bool, int, float]]:
        """Pull file from device to local machine."""
        try:
            pull_command = f"adb -s {{device}} pull {shlex.quote(device_path)} {shlex.quote(str(local_path))}"
            pull_result = await self.adb_manager.execute_adb_command(pull_command)

            if pull_result["success"] and local_path.exists():
                file_size = local_path.stat().st_size
                return {
                    "local_path": str(local_path),
                    "file_size_bytes": file_size,
                    "file_size_mb": round(file_size / (1024 * 1024), 2),
                }
            else:
                return {
                    "pull_failed": True,
                    "pull_error": pull_result.get("stderr", "Unknown pull error"),
                }

        except Exception as e:
            return {
                "pull_failed": True,
                "pull_error": f"Pull operation failed: {str(e)}",
            }


class VideoRecorder:
    """Advanced screen recording with lifecycle management."""

    def __init__(self, adb_manager: ADBManager, output_dir: str = "./assets") -> None:
        self.adb_manager = adb_manager
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.active_recordings: Dict[str, RecordingInfo] = {}

    async def start_recording(
        self,
        filename: Optional[str] = None,
        time_limit: int = 180,  # seconds
        bit_rate: Optional[str] = None,
        size_limit: Optional[str] = None,
        verbose: bool = False,
    ) -> RecordingResult:
        """
        Start screen recording session.

        Args:
            filename: Output filename (auto-generated if None)
            time_limit: Maximum recording time in seconds (3 min default)
            bit_rate: Video bit rate (e.g., '4M' for 4 Mbps)
            size_limit: Resolution limit (e.g., '720x1280')
            verbose: Enable verbose output
        """
        try:
            # Generate filename if not provided
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"recording_{timestamp}.mp4"

            # Ensure filename has .mp4 extension
            if not filename.endswith(".mp4"):
                filename = f"{filename}.mp4"

            device_path = f"/sdcard/{filename}"
            local_path = self.output_dir / filename

            # Build recording command
            options = []
            if bit_rate:
                options.extend(["--bit-rate", bit_rate])
            if size_limit:
                options.extend(["--size", size_limit])
            if verbose:
                options.append("--verbose")
            if time_limit:
                options.extend(["--time-limit", str(time_limit)])

            options_str = " ".join(options)
            record_command = (
                f"adb -s {{device}} shell screenrecord {options_str} {device_path}"
            )

            # Format command with device ID
            formatted_command = record_command.format(
                device=self.adb_manager.selected_device
            )
            cmd_parts = shlex.split(formatted_command)

            # Start recording process
            process = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Store recording info
            recording_id = f"{self.adb_manager.selected_device}_{filename}"
            self.active_recordings[recording_id] = {
                "process": process,
                "filename": filename,
                "device_path": device_path,
                "local_path": local_path,
                "start_time": datetime.now(),
                "time_limit": time_limit,
                "options": options_str,
            }

            return {
                "success": True,
                "action": "start_recording",
                "recording_id": recording_id,
                "filename": filename,
                "device_path": device_path,
                "time_limit": time_limit,
                "bit_rate": bit_rate,
                "size_limit": size_limit,
                "process_id": process.pid,
            }

        except Exception as e:
            logger.error(f"Start recording failed: {e}")
            return {"success": False, "error": f"Failed to start recording: {str(e)}"}

    async def stop_recording(
        self, recording_id: Optional[str] = None, pull_to_local: bool = True
    ) -> RecordingResult:
        """
        Stop active recording session.

        Args:
            recording_id: Specific recording to stop (stops all if None)
            pull_to_local: Download recording to local machine
        """
        try:
            if recording_id is None:
                # Stop all active recordings
                results: List[Dict[str, Any]] = []
                for rid in list(self.active_recordings.keys()):
                    result = await self._stop_single_recording(rid, pull_to_local)
                    results.append(dict(result))

                return {
                    "success": True,
                    "action": "stop_all_recordings",
                    "recordings_stopped": len(results),
                    "results": results,
                }
            else:
                # Stop specific recording
                return await self._stop_single_recording(recording_id, pull_to_local)

        except Exception as e:
            logger.error(f"Stop recording failed: {e}")
            return {"success": False, "error": f"Failed to stop recording: {str(e)}"}

    async def _stop_single_recording(
        self, recording_id: str, pull_to_local: bool
    ) -> RecordingResult:
        """Stop a single recording session."""
        if recording_id not in self.active_recordings:
            return {
                "success": False,
                "error": f"Recording {recording_id} not found",
                "active_recordings": list(self.active_recordings.keys()),
            }

        recording_info = self.active_recordings[recording_id]
        process = recording_info["process"]

        try:
            # Send interrupt signal to stop recording
            process.terminate()

            # Wait for process to finish
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10.0)

            # Calculate recording duration
            duration = datetime.now() - recording_info["start_time"]

            result: RecordingResult = {
                "success": True,
                "action": "stop_recording",
                "recording_id": recording_id,
                "filename": recording_info["filename"],
                "duration_seconds": duration.total_seconds(),
                "device_path": recording_info["device_path"],
            }

            # Pull to local machine if requested
            if pull_to_local:
                # Wait a moment for file to be fully written
                await asyncio.sleep(2)

                pull_result = await self._pull_file_from_device(
                    recording_info["device_path"], recording_info["local_path"]
                )
                if "local_path" in pull_result:
                    result["local_path"] = str(pull_result["local_path"])
                if "file_size_bytes" in pull_result:
                    result["file_size_bytes"] = int(pull_result["file_size_bytes"])
                if "file_size_mb" in pull_result:
                    result["file_size_mb"] = float(pull_result["file_size_mb"])
                if "pull_failed" in pull_result:
                    result["pull_failed"] = bool(pull_result["pull_failed"])
                if "pull_error" in pull_result:
                    result["pull_error"] = str(pull_result["pull_error"])

                # Clean up device file
                cleanup_command = (
                    f"adb -s {{device}} shell rm {recording_info['device_path']}"
                )
                await self.adb_manager.execute_adb_command(cleanup_command)

            # Clean up
            del self.active_recordings[recording_id]

            return result

        except asyncio.TimeoutError:
            # Force kill if graceful stop fails
            process.kill()
            del self.active_recordings[recording_id]

            return {
                "success": False,
                "error": "Recording stop timed out - force killed",
                "recording_id": recording_id,
            }
        except Exception as e:
            logger.error(f"Stop single recording failed: {e}")
            # Clean up the recording even on error to prevent orphaned recordings
            del self.active_recordings[recording_id]
            return {
                "success": False,
                "error": f"Failed to stop recording {recording_id}: {str(e)}",
            }

    async def _pull_file_from_device(
        self, device_path: str, local_path: Path
    ) -> Dict[str, Union[str, bool, int, float]]:
        """Pull recording file from device to local machine."""
        try:
            pull_command = f"adb -s {{device}} pull {shlex.quote(device_path)} {shlex.quote(str(local_path))}"
            pull_result = await self.adb_manager.execute_adb_command(pull_command)

            if pull_result["success"] and local_path.exists():
                file_size = local_path.stat().st_size
                return {
                    "local_path": str(local_path),
                    "file_size_bytes": file_size,
                    "file_size_mb": round(file_size / (1024 * 1024), 2),
                }
            else:
                return {
                    "pull_failed": True,
                    "pull_error": pull_result.get("stderr", "Unknown pull error"),
                }

        except Exception as e:
            return {
                "pull_failed": True,
                "pull_error": f"Pull operation failed: {str(e)}",
            }

    async def list_active_recordings(
        self,
    ) -> Dict[str, Union[bool, List[ActiveRecordingInfo], int, str]]:
        """List all currently active recording sessions."""
        try:
            active: List[ActiveRecordingInfo] = []
            for recording_id, info in self.active_recordings.items():
                duration = datetime.now() - info["start_time"]
                active.append(
                    {
                        "recording_id": recording_id,
                        "filename": info["filename"],
                        "duration_seconds": duration.total_seconds(),
                        "time_limit": info["time_limit"],
                        "device_path": info["device_path"],
                    }
                )

            return {"success": True, "active_recordings": active, "count": len(active)}

        except Exception as e:
            logger.error(f"List active recordings failed: {e}")
            return {"success": False, "error": f"Failed to list recordings: {str(e)}"}

    async def cleanup_all_recordings(self) -> RecordingResult:
        """Force cleanup of all active recordings."""
        try:
            cleanup_results = []

            for recording_id in list(self.active_recordings.keys()):
                recording_info = self.active_recordings[recording_id]
                process = recording_info["process"]

                try:
                    # Force terminate process
                    process.kill()

                    # Clean up device file
                    cleanup_command = (
                        f"adb -s {{device}} shell rm {recording_info['device_path']}"
                    )
                    cleanup_result = await self.adb_manager.execute_adb_command(
                        cleanup_command
                    )

                    cleanup_results.append(
                        {
                            "recording_id": recording_id,
                            "cleaned": True,
                            "details": cleanup_result.get("stderr", "Cleaned up"),
                        }
                    )

                except Exception as e:
                    cleanup_results.append(
                        {
                            "recording_id": recording_id,
                            "cleaned": False,
                            "error": str(e),
                        }
                    )

                # Remove from active recordings
                del self.active_recordings[recording_id]

            return {
                "success": True,
                "action": "cleanup_all",
                "cleaned_count": len(cleanup_results),
                "results": cleanup_results,
            }

        except Exception as e:
            logger.error(f"Cleanup all recordings failed: {e}")
            return {"success": False, "error": f"Cleanup failed: {str(e)}"}
