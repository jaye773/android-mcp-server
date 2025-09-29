"""Log monitoring and retrieval system for Android devices."""

from __future__ import annotations

import asyncio
import logging
import re
import shlex
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    TypedDict,
    Union,
    cast,
)

from .adb_manager import ADBCommands, ADBManager, _safe_process_terminate

logger = logging.getLogger(__name__)


# Type definitions for better type safety
class LogcatResult(TypedDict, total=False):
    """Type definition for logcat operation results."""

    success: bool
    action: str
    entries_count: int
    entries: List[Dict[str, Any]]
    filter_applied: Dict[str, Any]
    error: str
    details: Optional[str]


class MonitorInfo(TypedDict):
    """Type definition for active monitor session information."""

    process: asyncio.subprocess.Process
    task: asyncio.Task[None]
    start_time: datetime
    tag_filter: Optional[str]
    priority: str
    output_file: Optional[str]
    entries_processed: int


class MonitorResult(TypedDict, total=False):
    """Type definition for monitoring operation results."""

    success: bool
    action: str
    monitor_id: str
    tag_filter: Optional[str]
    priority: str
    output_file: Optional[str]
    process_id: Optional[int]
    duration_seconds: float
    entries_processed: int
    error: str
    active_monitors: List[str]
    monitors_stopped: int
    results: List[Dict[str, Any]]


class ActiveMonitorInfo(TypedDict):
    """Type definition for active monitor information in listings."""

    monitor_id: str
    duration_seconds: float
    tag_filter: Optional[str]
    priority: str
    entries_processed: int
    output_file: Optional[str]


class SearchResult(TypedDict, total=False):
    """Type definition for log search results."""

    success: bool
    action: str
    search_term: str
    matches_found: int
    entries: List[Dict[str, Any]]
    search_parameters: Dict[str, Union[str, int, None]]
    error: str


class LogLevel(Enum):
    VERBOSE = "V"
    DEBUG = "D"
    INFO = "I"
    WARN = "W"
    ERROR = "E"
    FATAL = "F"
    SILENT = "S"


@dataclass
class LogEntry:
    """Structured log entry."""

    timestamp: datetime
    level: LogLevel
    tag: str
    pid: int
    tid: int
    message: str
    raw_line: str


# Type aliases for callback functions (defined after LogEntry)
LogCallback = Union[Callable[[LogEntry], None], Callable[[LogEntry], Awaitable[None]]]


class LogMonitor:
    """Real-time log monitoring and filtering system."""

    def __init__(self, adb_manager: ADBManager, output_dir: str = "./logs") -> None:
        """Initialize LogMonitor with ADB manager and output directory.

        Args:
            adb_manager: ADB manager instance for device communication
            output_dir: Directory to store log files (default: ./logs)
        """
        self.adb_manager = adb_manager
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.active_monitors: Dict[str, MonitorInfo] = {}
        self.log_callbacks: List[LogCallback] = []

    async def get_logcat(
        self,
        tag_filter: Optional[str] = None,
        priority: str = "V",
        max_lines: int = 100,
        clear_first: bool = False,
        since_time: Optional[str] = None,
    ) -> LogcatResult:
        """Get device logs with filtering.

        Args:
            tag_filter: Filter by tag (e.g., 'ActivityManager')
            priority: Minimum log priority (V/D/I/W/E/F/S)
            max_lines: Maximum number of lines to return
            clear_first: Clear logcat buffer before reading
            since_time: Get logs since specific time (format: 'MM-DD HH:MM:SS.mmm')
        """
        try:
            # Clear logs if requested
            if clear_first:
                clear_result = await self._clear_logcat()
                if not clear_result["success"]:
                    details_val = clear_result.get("details")
                    return {
                        "success": False,
                        "action": "get_logcat",
                        "error": "Failed to clear logcat before retrieval",
                        "details": (
                            str(details_val) if details_val is not None else None
                        ),
                    }

            # Build logcat command
            options = []

            # Tag filter
            if tag_filter:
                options.append(f"-s {tag_filter}")

            # Priority filter
            options.append(f"*:{priority}")

            # Time filter
            if since_time:
                options.extend(["-t", shlex.quote(since_time)])

            # Dump existing logs (not follow mode)
            options.append("-d")

            # Line limit (using tail)
            options_str = " ".join(options)
            if max_lines:
                command = (
                    f"adb -s {{device}} logcat {options_str} | tail -n {max_lines}"
                )
            else:
                command = f"adb -s {{device}} logcat {options_str}"

            result = await self.adb_manager.execute_adb_command(command, timeout=30)

            if not result["success"]:
                return {
                    "success": False,
                    "action": "get_logcat",
                    "error": "Logcat command failed",
                    "details": result.get("stderr"),
                }

            # Parse log entries
            log_lines = result["stdout"].strip().split("\n")
            parsed_entries = []

            for line in log_lines:
                if line.strip():
                    entry = self._parse_log_line(line)
                    if entry:
                        parsed_entries.append(entry)

            return {
                "success": True,
                "action": "get_logcat",
                "entries_count": len(parsed_entries),
                "entries": [self._log_entry_to_dict(entry) for entry in parsed_entries],
                "filter_applied": {
                    "tag": tag_filter,
                    "priority": priority,
                    "max_lines": max_lines,
                    "since_time": since_time,
                },
            }

        except Exception as e:
            logger.error(f"Log retrieval failed: {e}")
            return {"success": False, "error": f"Log retrieval failed: {str(e)}"}

    async def start_log_monitoring(
        self,
        tag_filter: Optional[str] = None,
        priority: str = "I",
        output_file: Optional[str] = None,
        callback: Optional[LogCallback] = None,
    ) -> MonitorResult:
        """Start continuous log monitoring in background.

        Args:
            tag_filter: Filter by specific tags
            priority: Minimum log priority
            output_file: Save logs to file
            callback: Function to call for each log entry
        """
        try:
            # Generate monitor ID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            monitor_id = f"logmon_{self.adb_manager.selected_device}_{timestamp}"

            # Setup output file if specified
            log_file_path = None
            if output_file:
                if not output_file.endswith(".log"):
                    output_file = f"{output_file}.log"
                log_file_path = self.output_dir / output_file

            # Build command for continuous monitoring
            options = []
            if tag_filter:
                options.append(f"-s {tag_filter}")
            options.append(f"*:{priority}")

            # Clear buffer before starting
            await self._clear_logcat()

            options_str = " ".join(options)
            command = f"adb -s {{device}} logcat {options_str}"

            # Format command with device ID
            formatted_command = command.format(device=self.adb_manager.selected_device)
            cmd_parts = shlex.split(formatted_command)

            # Start monitoring process
            process = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Create monitoring task
            monitor_task = asyncio.create_task(
                self._monitor_logs(process, monitor_id, log_file_path, callback)
            )

            # Store monitor info
            self.active_monitors[monitor_id] = {
                "process": process,
                "task": monitor_task,
                "start_time": datetime.now(),
                "tag_filter": tag_filter,
                "priority": priority,
                "output_file": str(log_file_path) if log_file_path else None,
                "entries_processed": 0,
            }

            return {
                "success": True,
                "action": "start_log_monitoring",
                "monitor_id": monitor_id,
                "tag_filter": tag_filter,
                "priority": priority,
                "output_file": str(log_file_path) if log_file_path else None,
                "process_id": process.pid,
            }

        except Exception as e:
            logger.error(f"Start log monitoring failed: {e}")
            return {
                "success": False,
                "error": f"Failed to start log monitoring: {str(e)}",
            }

    async def _monitor_logs(
        self,
        process: asyncio.subprocess.Process,
        monitor_id: str,
        log_file_path: Optional[Path],
        callback: Optional[LogCallback],
    ) -> None:
        """Background task for processing log stream."""
        log_file = None
        if log_file_path:
            try:
                log_file = open(log_file_path, "w", encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to open log file {log_file_path}: {e}")

        try:
            while True:
                if not process.stdout:
                    break
                line = await process.stdout.readline()
                if not line:
                    break

                line_str = line.decode("utf-8").strip()
                if not line_str:
                    continue

                # Parse log entry
                entry = self._parse_log_line(line_str)
                if entry:
                    # Update counter
                    if monitor_id in self.active_monitors:
                        self.active_monitors[monitor_id]["entries_processed"] += 1

                    # Write to file
                    if log_file:
                        try:
                            log_file.write(f"{line_str}\n")
                            log_file.flush()
                        except Exception as e:
                            logger.error(f"Failed to write to log file: {e}")

                    # Call callback
                    if callback:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(entry)
                            else:
                                callback(entry)
                        except Exception as e:
                            logger.warning(f"Log callback failed: {e}")

                    # Call registered callbacks
                    for cb in self.log_callbacks:
                        try:
                            if asyncio.iscoroutinefunction(cb):
                                await cb(entry)
                            else:
                                cb(entry)
                        except Exception as e:
                            logger.warning(f"Registered callback failed: {e}")

        except Exception as e:
            logger.error(f"Log monitoring error: {e}")
        finally:
            if log_file:
                try:
                    log_file.close()
                except Exception as e:
                    logger.error(f"Failed to close log file: {e}")

    def _parse_log_line(self, line: str) -> Optional[LogEntry]:
        """Parse Android log line format.

        Standard format: MM-DD HH:MM:SS.mmm PID TID LEVEL TAG : MESSAGE
        """
        # Regex pattern for standard logcat format
        pattern = r"(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+(\d+)\s+(\d+)\s+([VDIWEF])\s+([^:]+):\s*(.*)"

        match = re.match(pattern, line)
        if not match:
            # Try alternative format without milliseconds
            alt_pattern = r"(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(\d+)\s+(\d+)\s+([VDIWEF])\s+([^:]+):\s*(.*)"
            match = re.match(alt_pattern, line)
            if not match:
                return None

        try:
            timestamp_str, pid_str, tid_str, level_str, tag, message = match.groups()

            # Parse timestamp (add current year)
            current_year = datetime.now().year
            if "." in timestamp_str:
                timestamp = datetime.strptime(
                    f"{current_year}-{timestamp_str}", "%Y-%m-%d %H:%M:%S.%f"
                )
            else:
                timestamp = datetime.strptime(
                    f"{current_year}-{timestamp_str}", "%Y-%m-%d %H:%M:%S"
                )

            return LogEntry(
                timestamp=timestamp,
                level=LogLevel(level_str),
                tag=tag.strip(),
                pid=int(pid_str),
                tid=int(tid_str),
                message=message.strip(),
                raw_line=line,
            )

        except (ValueError, IndexError) as e:
            logger.debug(f"Failed to parse log line: {line} - {e}")
            return None

    def _log_entry_to_dict(self, entry: LogEntry) -> Dict[str, Union[str, int]]:
        """Convert LogEntry to dictionary."""
        return {
            "timestamp": entry.timestamp.isoformat(),
            "level": entry.level.value,
            "tag": entry.tag,
            "pid": entry.pid,
            "tid": entry.tid,
            "message": entry.message,
        }

    async def stop_log_monitoring(
        self, monitor_id: Optional[str] = None
    ) -> MonitorResult:
        """Stop log monitoring session(s).

        Args:
            monitor_id: Specific monitor to stop (stops all if None)
        """
        try:
            if monitor_id is None:
                # Stop all monitors
                results: List[Dict[str, Any]] = []
                for mid in list(self.active_monitors.keys()):
                    result = await self._stop_single_monitor(mid)
                    results.append(cast(Dict[str, Any], result))

                return {
                    "success": True,
                    "action": "stop_all_monitoring",
                    "monitors_stopped": len(results),
                    "results": results,
                }
            else:
                # Stop specific monitor
                return await self._stop_single_monitor(monitor_id)

        except Exception as e:
            logger.error(f"Stop monitoring failed: {e}")
            return {"success": False, "error": f"Failed to stop monitoring: {str(e)}"}

    async def _stop_single_monitor(self, monitor_id: str) -> MonitorResult:
        """Stop a single monitoring session."""
        if monitor_id not in self.active_monitors:
            return {
                "success": False,
                "error": f"Monitor {monitor_id} not found",
                "active_monitors": list(self.active_monitors.keys()),
            }

        monitor_info = self.active_monitors[monitor_id]
        process = monitor_info["process"]
        task = monitor_info["task"]

        try:
            # Stop the process
            await _safe_process_terminate(process)

            cancel_result = task.cancel()
            if asyncio.iscoroutine(cancel_result):
                await cancel_result

            # Wait for cleanup
            try:
                await asyncio.wait_for(task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

            # Calculate stats
            duration = datetime.now() - monitor_info["start_time"]
            entries_processed = monitor_info["entries_processed"]

            result: MonitorResult = {
                "success": True,
                "action": "stop_monitoring",
                "monitor_id": monitor_id,
                "duration_seconds": duration.total_seconds(),
                "entries_processed": entries_processed,
                "output_file": monitor_info["output_file"],
            }

            # Clean up
            del self.active_monitors[monitor_id]

            return result

        except Exception as e:
            logger.error(f"Stop single monitor failed: {e}")
            return {
                "success": False,
                "error": f"Failed to stop monitor {monitor_id}: {str(e)}",
            }

    async def _clear_logcat(self) -> Dict[str, Union[bool, str]]:
        """Clear the logcat buffer."""
        try:
            command = ADBCommands.LOGCAT_CLEAR
            result = await self.adb_manager.execute_adb_command(command)

            success_flag = bool(result.get("success"))
            details_value = (
                "Logcat buffer cleared"
                if success_flag
                else (result.get("stderr") or "Logcat clear failed")
            )
            return {
                "success": success_flag,
                "action": "clear_logcat",
                "details": str(details_value),
            }

        except Exception as e:
            logger.error(f"Clear logcat failed: {e}")
            return {"success": False, "error": f"Failed to clear logcat: {str(e)}"}

    async def list_active_monitors(
        self,
    ) -> Dict[str, Union[bool, List[ActiveMonitorInfo], int, str]]:
        """List all active monitoring sessions."""
        try:
            active: List[ActiveMonitorInfo] = []
            for monitor_id, info in self.active_monitors.items():
                duration = datetime.now() - info["start_time"]
                active.append(
                    {
                        "monitor_id": monitor_id,
                        "duration_seconds": duration.total_seconds(),
                        "tag_filter": info["tag_filter"],
                        "priority": info["priority"],
                        "entries_processed": info["entries_processed"],
                        "output_file": info["output_file"],
                    }
                )

            return {"success": True, "active_monitors": active, "count": len(active)}

        except Exception as e:
            logger.error(f"List active monitors failed: {e}")
            return {"success": False, "error": f"Failed to list monitors: {str(e)}"}

    def add_log_callback(self, callback: LogCallback) -> None:
        """Add a callback function for log entries."""
        self.log_callbacks.append(callback)

    def remove_log_callback(self, callback: LogCallback) -> None:
        """Remove a callback function."""
        if callback in self.log_callbacks:
            self.log_callbacks.remove(callback)

    async def search_logs(
        self,
        search_term: str,
        tag_filter: Optional[str] = None,
        priority: str = "V",
        max_results: int = 50,
    ) -> SearchResult:
        """Search through recent logs for specific terms.

        Args:
            search_term: Text to search for in log messages
            tag_filter: Filter by specific tag
            priority: Minimum log priority
            max_results: Maximum number of results to return
        """
        try:
            # Get recent logs
            logs_result = await self.get_logcat(
                tag_filter=tag_filter,
                priority=priority,
                max_lines=1000,  # Search in last 1000 lines
                clear_first=False,
            )

            if not logs_result["success"]:
                return {
                    "success": False,
                    "action": "search_logs",
                    "search_term": search_term,
                    "matches_found": 0,
                    "entries": [],
                    "search_parameters": {
                        "tag_filter": tag_filter,
                        "priority": priority,
                        "max_results": max_results,
                    },
                    "error": logs_result.get("error", "Log retrieval failed"),
                }

            # Search through entries
            matching_entries = []
            search_lower = search_term.lower()

            for entry_dict in logs_result["entries"]:
                message_lower = entry_dict["message"].lower()
                tag_lower = entry_dict["tag"].lower()

                if search_lower in message_lower or search_lower in tag_lower:
                    entry_dict["match_reason"] = []
                    if search_lower in message_lower:
                        entry_dict["match_reason"].append("message")
                    if search_lower in tag_lower:
                        entry_dict["match_reason"].append("tag")

                    matching_entries.append(entry_dict)

                    if len(matching_entries) >= max_results:
                        break

            return {
                "success": True,
                "action": "search_logs",
                "search_term": search_term,
                "matches_found": len(matching_entries),
                "entries": matching_entries,
                "search_parameters": {
                    "tag_filter": tag_filter,
                    "priority": priority,
                    "max_results": max_results,
                },
            }

        except Exception as e:
            logger.error(f"Log search failed: {e}")
            return {"success": False, "error": f"Log search failed: {str(e)}"}
