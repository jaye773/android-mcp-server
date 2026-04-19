"""Extended unit tests for LogMonitor to achieve comprehensive coverage."""

import asyncio
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, mock_open, patch

import pytest

from src.adb_manager import ADBManager
from src.log_monitor import LogCallback, LogEntry, LogLevel, LogMonitor


class ExtendedMockADB:
    """Extended mock ADB manager for comprehensive testing."""

    def __init__(self, fail_clear=False, fail_logcat=False, timeout_logcat=False):
        self.selected_device = "emulator-5554"
        self.fail_clear = fail_clear
        self.fail_logcat = fail_logcat
        self.timeout_logcat = timeout_logcat
        self.call_count = 0

    async def execute_adb_command(
        self, command, timeout=30, capture_output=True, check_device=True
    ):
        self.call_count += 1

        # Handle clear logcat failures
        if "logcat -c" in command and self.fail_clear:
            return {
                "success": False,
                "stderr": "Failed to clear logcat",
                "returncode": 1,
            }

        # Handle logcat command failures
        if "logcat" in command and self.fail_logcat:
            return {
                "success": False,
                "stderr": "Logcat command failed",
                "returncode": 1,
            }

        # Handle timeout scenarios
        if "logcat" in command and self.timeout_logcat:
            await asyncio.sleep(0.1)  # Simulate timeout behavior
            raise asyncio.TimeoutError("Command timed out")

        # Standard successful responses
        if "logcat -c" in command:
            return {"success": True, "stdout": "", "stderr": "", "returncode": 0}

        if "logcat" in command and "-d" in command:
            # Provide various log formats for parsing tests
            return {
                "success": True,
                "stdout": (
                    "01-01 12:00:00.000  123  456 I MyApp: Test message 1\n"
                    "01-01 12:00:01.500  789  012 E SysApp: Error occurred\n"
                    "01-01 12:00:02  234  567 W TestTag: Warning message\n"  # No milliseconds
                    "Invalid log line format\n"  # Unparseable line
                    "01-01 12:00:03.999  345  678 D Debug: Multi-word tag test\n"
                    "01-01 12:00:04.123  456  789 F Fatal: Critical error\n"
                ),
                "stderr": "",
                "returncode": 0,
            }

        # Default success response
        return {"success": True, "stdout": "", "stderr": "", "returncode": 0}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_logcat_clear_failure():
    """Test get_logcat when clear operation fails."""
    adb = ExtendedMockADB(fail_clear=True)
    lm = LogMonitor(adb_manager=adb)

    result = await lm.get_logcat(clear_first=True)

    assert result["success"] is False
    assert "Failed to clear logcat" in result.get("details", "")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_logcat_command_failure():
    """Test get_logcat when logcat command fails."""
    adb = ExtendedMockADB(fail_logcat=True)
    lm = LogMonitor(adb_manager=adb)

    result = await lm.get_logcat()

    assert result["success"] is False
    assert "Logcat command failed" in result["error"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_logcat_with_since_time():
    """Test get_logcat with time filtering."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    result = await lm.get_logcat(since_time="01-01 12:00:00.000")

    assert result["success"] is True
    assert result["filter_applied"]["since_time"] == "01-01 12:00:00.000"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_logcat_no_max_lines():
    """Test get_logcat without line limit."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    result = await lm.get_logcat(max_lines=0)

    assert result["success"] is True
    # Should not use tail command when max_lines is 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_logcat_exception_handling():
    """Test get_logcat with unexpected exceptions."""
    adb = AsyncMock()
    adb.selected_device = "test-device"
    adb.execute_adb_command.side_effect = Exception("Unexpected error")

    lm = LogMonitor(adb_manager=adb)

    result = await lm.get_logcat()

    assert result["success"] is False
    assert "Log retrieval failed" in result["error"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_log_monitoring_full_workflow():
    """Test complete log monitoring startup process."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    # Mock subprocess creation to avoid actual adb calls
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_process.stdout = MagicMock()
    mock_process.stderr = MagicMock()

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        # Test with output file that doesn't end in .log
        result = await lm.start_log_monitoring(
            tag_filter="TestApp", priority="W", output_file="test_logs"
        )

    assert result["success"] is True
    assert "logmon_" in result["monitor_id"]
    assert result["tag_filter"] == "TestApp"
    assert result["priority"] == "W"
    assert result["output_file"].endswith("test_logs.log")
    assert result["process_id"] is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_log_monitoring_with_callback():
    """Test log monitoring with callback function."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    callback_calls = []

    def test_callback(entry: LogEntry):
        callback_calls.append(entry)

    # Mock subprocess creation to avoid actual adb calls
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_process.stdout = MagicMock()
    mock_process.stderr = MagicMock()

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        result = await lm.start_log_monitoring(callback=test_callback)

    assert result["success"] is True
    # Callback will be tested in the monitor task


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_log_monitoring_exception():
    """Test start_log_monitoring with process creation failure."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    # Mock asyncio.create_subprocess_exec to raise an exception
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_exec.side_effect = Exception("Process creation failed")

        result = await lm.start_log_monitoring()

        assert result["success"] is False
        assert "Failed to start log monitoring" in result["error"]


@pytest.mark.unit
def test_parse_log_line_various_formats():
    """Test log line parsing with different formats."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    # Test standard format with milliseconds
    line1 = "01-01 12:00:00.123  123  456 I TestTag: Test message"
    entry1 = lm._parse_log_line(line1)
    assert entry1 is not None
    assert entry1.level == LogLevel.INFO
    assert entry1.tag == "TestTag"
    assert entry1.message == "Test message"
    assert entry1.pid == 123
    assert entry1.tid == 456

    # Test format without milliseconds (alternative format)
    line2 = "01-01 12:00:00  789  012 E ErrorTag: Error message"
    entry2 = lm._parse_log_line(line2)
    assert entry2 is not None
    assert entry2.level == LogLevel.ERROR
    assert entry2.tag == "ErrorTag"
    assert entry2.message == "Error message"

    # Test unparseable line
    line3 = "Invalid log format"
    entry3 = lm._parse_log_line(line3)
    assert entry3 is None

    # Test parsing with value errors (malformed numbers)
    line4 = "01-01 12:00:00.123  abc  def I Tag: Message"
    entry4 = lm._parse_log_line(line4)
    assert entry4 is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_monitor_logs_file_operations():
    """Test the background monitoring task with file operations."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    # Create a temporary directory for testing
    temp_dir = Path(tempfile.mkdtemp())
    log_file_path = temp_dir / "test.log"

    try:
        # Mock process with stdout
        mock_process = AsyncMock()
        mock_process.stdout.readline.side_effect = [
            b"01-01 12:00:00.123  123  456 I Test: Message 1\n",
            b"01-01 12:00:01.456  789  012 E Test: Message 2\n",
            b"",  # End of stream
        ]

        callback_calls = []

        def test_callback(entry: LogEntry):
            callback_calls.append(entry.message)

        # Start monitoring task
        monitor_id = "test_monitor"
        lm.active_monitors[monitor_id] = {"entries_processed": 0}

        # Run the monitoring task
        await lm._monitor_logs(mock_process, monitor_id, log_file_path, test_callback)

        # Check that file was created and contains log entries
        assert log_file_path.exists()
        content = log_file_path.read_text()
        assert "Message 1" in content
        assert "Message 2" in content

        # Check callback was called
        assert len(callback_calls) == 2
        assert "Message 1" in callback_calls
        assert "Message 2" in callback_calls

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_monitor_logs_file_error_handling():
    """Test monitoring with file operation errors."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    # Use an invalid path that will cause file operations to fail
    invalid_path = Path("/invalid/path/test.log")

    mock_process = AsyncMock()
    mock_process.stdout.readline.side_effect = [
        b"01-01 12:00:00.123  123  456 I Test: Message\n",
        b"",  # End of stream
    ]

    monitor_id = "test_monitor"
    lm.active_monitors[monitor_id] = {"entries_processed": 0}

    # Should not raise exception even with file errors
    await lm._monitor_logs(mock_process, monitor_id, invalid_path, None)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_monitor_logs_callback_errors():
    """Test monitoring with callback errors."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    mock_process = AsyncMock()
    mock_process.stdout.readline.side_effect = [
        b"01-01 12:00:00.123  123  456 I Test: Message\n",
        b"",
    ]

    def failing_callback(entry: LogEntry):
        raise Exception("Callback error")

    monitor_id = "test_monitor"
    lm.active_monitors[monitor_id] = {"entries_processed": 0}

    # Should handle callback errors gracefully
    await lm._monitor_logs(mock_process, monitor_id, None, failing_callback)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_monitor_logs_async_callback():
    """Test monitoring with async callback functions."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    mock_process = AsyncMock()
    mock_process.stdout.readline.side_effect = [
        b"01-01 12:00:00.123  123  456 I Test: Message\n",
        b"",
    ]

    async_calls = []

    async def async_callback(entry: LogEntry):
        async_calls.append(entry.message)

    monitor_id = "test_monitor"
    lm.active_monitors[monitor_id] = {"entries_processed": 0}

    await lm._monitor_logs(mock_process, monitor_id, None, async_callback)

    assert len(async_calls) == 1
    assert "Message" in async_calls[0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_monitor_logs_registered_callbacks():
    """Test monitoring with registered global callbacks."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    mock_process = AsyncMock()
    mock_process.stdout.readline.side_effect = [
        b"01-01 12:00:00.123  123  456 I Test: Message\n",
        b"",
    ]

    global_calls = []

    def global_callback(entry: LogEntry):
        global_calls.append(entry.tag)

    # Add global callback (async method)
    await lm.add_log_callback(global_callback)

    monitor_id = "test_monitor"
    lm.active_monitors[monitor_id] = {"entries_processed": 0}

    await lm._monitor_logs(mock_process, monitor_id, None, None)

    assert len(global_calls) == 1
    assert "Test" in global_calls


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stop_single_monitor_not_found():
    """Test stopping a monitor that doesn't exist."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    result = await lm._stop_single_monitor("nonexistent_monitor")

    assert result["success"] is False
    assert "not found" in result["error"]
    assert "active_monitors" in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stop_single_monitor_success():
    """Test successfully stopping a single monitor."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    # Create mock process and task with proper mock methods
    mock_process = Mock()
    mock_process.terminate.return_value = None

    # Create a mock task
    mock_task = Mock()
    mock_task.cancel.return_value = None

    monitor_id = "test_monitor"
    start_time = datetime.now()

    lm.active_monitors[monitor_id] = {
        "process": mock_process,
        "task": mock_task,
        "start_time": start_time,
        "entries_processed": 42,
        "output_file": "/path/to/log.txt",
    }

    # Mock asyncio.wait_for to avoid awaitable issues
    with patch("asyncio.wait_for") as mock_wait:
        mock_wait.return_value = None  # Simulate successful completion

        result = await lm._stop_single_monitor(monitor_id)

        assert result["success"] is True
        assert result["monitor_id"] == monitor_id
        assert result["entries_processed"] == 42
        assert result["output_file"] == "/path/to/log.txt"
        assert result["duration_seconds"] > 0

        # Check cleanup
        assert monitor_id not in lm.active_monitors
        mock_process.terminate.assert_called_once()
        mock_task.cancel.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stop_single_monitor_exception():
    """Test stop_single_monitor with process termination errors."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    # Create mock process that raises exception on terminate
    mock_process = Mock()
    mock_process.terminate.side_effect = Exception("Process error")

    mock_task = AsyncMock()
    mock_task.cancel.return_value = None

    monitor_id = "test_monitor"
    lm.active_monitors[monitor_id] = {
        "process": mock_process,
        "task": mock_task,
        "start_time": datetime.now(),
        "entries_processed": 0,
        "output_file": None,
    }

    result = await lm._stop_single_monitor(monitor_id)

    assert result["success"] is False
    assert "Failed to stop monitor" in result["error"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stop_log_monitoring_all():
    """Test stopping all monitors."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    # Create multiple mock monitors
    for i in range(3):
        monitor_id = f"monitor_{i}"
        mock_process = Mock()
        mock_process.terminate.return_value = None
        mock_task = AsyncMock()
        mock_task.cancel.return_value = None

        lm.active_monitors[monitor_id] = {
            "process": mock_process,
            "task": mock_task,
            "start_time": datetime.now(),
            "entries_processed": i * 10,
            "output_file": None,
        }

    result = await lm.stop_log_monitoring()  # No monitor_id = stop all

    assert result["success"] is True
    assert result["action"] == "stop_all_monitoring"
    assert result["monitors_stopped"] == 3
    assert len(result["results"]) == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stop_log_monitoring_specific():
    """Test stopping a specific monitor."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    monitor_id = "specific_monitor"
    mock_process = Mock()
    mock_process.terminate.return_value = None
    mock_task = Mock()
    mock_task.cancel.return_value = None

    lm.active_monitors[monitor_id] = {
        "process": mock_process,
        "task": mock_task,
        "start_time": datetime.now(),
        "entries_processed": 25,
        "output_file": None,
    }

    # Mock asyncio.wait_for to avoid awaitable issues
    with patch("asyncio.wait_for") as mock_wait:
        mock_wait.return_value = None

        result = await lm.stop_log_monitoring(monitor_id)

        assert result["success"] is True
        assert result["monitor_id"] == monitor_id
        assert result["entries_processed"] == 25


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stop_log_monitoring_exception():
    """Test stop_log_monitoring with unexpected exception."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    # Mock the _stop_single_monitor to raise exception
    with patch.object(lm, "_stop_single_monitor") as mock_stop:
        mock_stop.side_effect = Exception("Stop error")

        result = await lm.stop_log_monitoring("test_id")

        assert result["success"] is False
        assert "Failed to stop monitoring" in result["error"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clear_logcat_exception():
    """Test _clear_logcat with exception handling."""
    adb = AsyncMock()
    adb.execute_adb_command.side_effect = Exception("Clear error")

    lm = LogMonitor(adb_manager=adb)

    result = await lm._clear_logcat()

    assert result["success"] is False
    assert "Failed to clear logcat" in result["error"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_active_monitors_success():
    """Test listing active monitors."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    # Add some active monitors
    start_time = datetime.now()
    for i in range(2):
        monitor_id = f"monitor_{i}"
        lm.active_monitors[monitor_id] = {
            "start_time": start_time,
            "tag_filter": f"Tag{i}",
            "priority": "I",
            "entries_processed": i * 5,
            "output_file": f"/path/log{i}.txt" if i == 0 else None,
        }

    result = await lm.list_active_monitors()

    assert result["success"] is True
    assert result["count"] == 2
    assert len(result["active_monitors"]) == 2

    # Check first monitor details
    monitor_info = result["active_monitors"][0]
    assert monitor_info["monitor_id"] == "monitor_0"
    assert monitor_info["tag_filter"] == "Tag0"
    assert monitor_info["priority"] == "I"
    assert monitor_info["entries_processed"] == 0
    assert monitor_info["output_file"] == "/path/log0.txt"
    assert monitor_info["duration_seconds"] >= 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_active_monitors_exception():
    """Test list_active_monitors with exception handling."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    # Force an exception by corrupting the active_monitors dict
    lm.active_monitors = {"invalid": "data"}

    result = await lm.list_active_monitors()

    assert result["success"] is False
    assert "Failed to list monitors" in result["error"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_callback_management():
    """Test adding and removing log callbacks."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    def callback1(entry):
        pass

    def callback2(entry):
        pass

    # Add callbacks (async methods)
    await lm.add_log_callback(callback1)
    await lm.add_log_callback(callback2)

    assert len(lm.log_callbacks) == 2
    assert callback1 in lm.log_callbacks
    assert callback2 in lm.log_callbacks

    # Remove callback (async method)
    await lm.remove_log_callback(callback1)
    assert len(lm.log_callbacks) == 1
    assert callback1 not in lm.log_callbacks
    assert callback2 in lm.log_callbacks

    # Try to remove non-existent callback (should not raise error)
    await lm.remove_log_callback(callback1)
    assert len(lm.log_callbacks) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_logs_get_logcat_failure():
    """Test search_logs when get_logcat fails."""
    adb = ExtendedMockADB(fail_logcat=True)
    lm = LogMonitor(adb_manager=adb)

    result = await lm.search_logs("error", tag_filter="TestTag")

    assert result["success"] is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_logs_tag_matching():
    """Test search_logs with tag-based matching."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    result = await lm.search_logs("SysApp", max_results=2)

    assert result["success"] is True
    assert result["search_term"] == "SysApp"
    assert result["matches_found"] >= 1

    # Check that matches have the expected structure
    if result["entries"]:
        entry = result["entries"][0]
        assert "match_reason" in entry
        assert "tag" in entry["match_reason"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_logs_max_results_limit():
    """Test search_logs respects max_results limit."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    # Search for a term that appears in multiple log entries
    result = await lm.search_logs("message", max_results=1)

    assert result["success"] is True
    assert len(result["entries"]) <= 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_logs_exception():
    """Test search_logs with exception handling."""
    adb = AsyncMock()
    adb.execute_adb_command.side_effect = Exception("Search error")

    lm = LogMonitor(adb_manager=adb)

    result = await lm.search_logs("test")

    assert result["success"] is False
    # The error actually comes from get_logcat, which is called by search_logs
    assert "Log retrieval failed" in result["error"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_concurrent_monitoring_sessions():
    """Test multiple concurrent monitoring sessions setup."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    # Manually add multiple monitors to test management
    for i in range(3):
        monitor_id = f"monitor_{i}"
        mock_process = Mock()
        mock_process.terminate.return_value = None
        mock_task = AsyncMock()
        mock_task.cancel.return_value = None

        lm.active_monitors[monitor_id] = {
            "process": mock_process,
            "task": mock_task,
            "start_time": datetime.now(),
            "tag_filter": f"App{i}",
            "priority": "W",
            "entries_processed": i * 5,
            "output_file": None,
        }

    # Check active monitors
    monitor_list = await lm.list_active_monitors()
    assert monitor_list["count"] == 3

    # Stop all monitors
    stop_result = await lm.stop_log_monitoring()
    assert stop_result["success"] is True
    assert stop_result["monitors_stopped"] == 3


@pytest.mark.unit
def test_log_entry_to_dict():
    """Test conversion of LogEntry to dictionary."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    timestamp = datetime(2024, 1, 1, 12, 0, 0)
    entry = LogEntry(
        timestamp=timestamp,
        level=LogLevel.WARN,  # Use WARN instead of WARNING
        tag="TestTag",
        pid=123,
        tid=456,
        message="Test message",
        raw_line="01-01 12:00:00.000  123  456 W TestTag: Test message",
    )

    result = lm._log_entry_to_dict(entry)

    assert result["timestamp"] == timestamp.isoformat()
    assert result["level"] == "W"
    assert result["tag"] == "TestTag"
    assert result["pid"] == 123
    assert result["tid"] == 456
    assert result["message"] == "Test message"


@pytest.mark.unit
def test_parse_log_line_edge_cases():
    """Test log parsing with edge cases and malformed data."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    # Test empty/whitespace lines
    assert lm._parse_log_line("") is None
    assert lm._parse_log_line("   ") is None

    # Test completely malformed line
    assert lm._parse_log_line("not a log line at all") is None

    # Test line with invalid timestamp format
    invalid_line = "invalid-timestamp  123  456 I Tag: Message"
    assert lm._parse_log_line(invalid_line) is None

    # Test line with non-numeric PID/TID
    invalid_nums = "01-01 12:00:00.123  abc  def I Tag: Message"
    assert lm._parse_log_line(invalid_nums) is None


@pytest.mark.unit
def test_output_directory_creation():
    """Test output directory creation during initialization."""
    # Create temp directory for testing
    temp_dir = Path(tempfile.mkdtemp())
    test_output_dir = temp_dir / "test_logs"

    try:
        adb = ExtendedMockADB()
        lm = LogMonitor(adb_manager=adb, output_dir=str(test_output_dir))

        # Directory should be created
        assert test_output_dir.exists()
        assert test_output_dir.is_dir()

    finally:
        shutil.rmtree(temp_dir)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_large_log_buffer_handling():
    """Test handling of large log entries and buffers."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    # Test with large max_lines parameter
    result = await lm.get_logcat(max_lines=10000)

    assert result["success"] is True
    # Should handle large buffer requests gracefully


@pytest.mark.unit
@pytest.mark.asyncio
async def test_priority_filtering():
    """Test log priority filtering functionality."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    # Test different priority levels
    priorities = ["V", "D", "I", "W", "E", "F", "S"]

    for priority in priorities:
        result = await lm.get_logcat(priority=priority)
        assert result["success"] is True
        assert result["filter_applied"]["priority"] == priority


@pytest.mark.unit
@pytest.mark.asyncio
async def test_monitor_task_cancellation_timeout():
    """Test monitor task cancellation with timeout."""
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    # Create a mock task that doesn't respond to cancellation quickly
    mock_task = AsyncMock()
    mock_task.cancel.return_value = None

    mock_process = Mock()
    mock_process.terminate.return_value = None

    # Mock asyncio.wait_for to raise TimeoutError
    with patch("asyncio.wait_for") as mock_wait:
        mock_wait.side_effect = asyncio.TimeoutError()

        monitor_id = "timeout_test"
        lm.active_monitors[monitor_id] = {
            "process": mock_process,
            "task": mock_task,
            "start_time": datetime.now(),
            "entries_processed": 0,
            "output_file": None,
        }

        result = await lm._stop_single_monitor(monitor_id)

        # Should still succeed despite timeout
        assert result["success"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_log_monitoring_does_not_call_logcat_c():
    """start_log_monitoring must not clear the shared logcat buffer.

    Regression test: previously this method issued `adb logcat -c`, which
    wipes the device-wide buffer and destroys backfill for any other active
    monitor on the same device.
    """
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    captured_cmds = []

    mock_process = MagicMock()
    mock_process.pid = 4321
    mock_process.stdout = MagicMock()
    mock_process.stderr = MagicMock()

    async def fake_exec(*args, **kwargs):
        captured_cmds.append(list(args))
        return mock_process

    # Also spy on adb.execute_adb_command so we can prove no
    # shared-buffer clear was issued either.
    seen_commands = []
    original_exec = adb.execute_adb_command

    async def spy(command, **kwargs):
        seen_commands.append(command)
        return await original_exec(command, **kwargs)

    adb.execute_adb_command = spy  # type: ignore[assignment]

    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
        result = await lm.start_log_monitoring()

    assert result["success"] is True

    # No subprocess was spawned with `-c` in its argv
    for argv in captured_cmds:
        assert "-c" not in argv, (
            f"start_log_monitoring spawned a command with -c: {argv}"
        )

    # No logcat -c command was issued via execute_adb_command
    assert not any("logcat -c" in c for c in seen_commands), (
        f"start_log_monitoring triggered a logcat clear: {seen_commands}"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_second_monitor_does_not_clear_first():
    """Starting monitor B must not wipe monitor A's buffered stream.

    Simulates two concurrent monitors, each with an independent mocked
    subprocess stdout. Monitor A is started and reads L1; then monitor B
    starts and both then read L2. Monitor A must see [L1, L2] and monitor
    B must see [L2]. The point is that starting B does not trigger a
    shared `logcat -c` that would affect A.
    """
    adb = ExtendedMockADB()
    lm = LogMonitor(adb_manager=adb)

    line_l1 = b"01-01 12:00:00.100  100  200 I AppA: L1\n"
    line_l2 = b"01-01 12:00:05.100  100  200 I AppA: L2\n"

    process_a = AsyncMock()
    process_a.pid = 111
    process_a.stdout.readline = AsyncMock(side_effect=[line_l1, line_l2, b""])

    process_b = AsyncMock()
    process_b.pid = 222
    process_b.stdout.readline = AsyncMock(side_effect=[line_l2, b""])

    processes_to_hand_out = [process_a, process_b]
    exec_argvs = []

    async def fake_exec(*args, **kwargs):
        exec_argvs.append(list(args))
        return processes_to_hand_out.pop(0)

    seen_commands = []
    original_exec = adb.execute_adb_command

    async def spy(command, **kwargs):
        seen_commands.append(command)
        return await original_exec(command, **kwargs)

    adb.execute_adb_command = spy  # type: ignore[assignment]

    a_entries = []
    b_entries = []

    def cb_a(entry: LogEntry):
        a_entries.append(entry.message)

    def cb_b(entry: LogEntry):
        b_entries.append(entry.message)

    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
        res_a = await lm.start_log_monitoring(callback=cb_a)
        assert res_a["success"] is True
        monitor_a_id = res_a["monitor_id"]
        a_task = lm.active_monitors[monitor_a_id]["task"]

        # Let monitor A's background task read L1 before monitor B starts
        await asyncio.sleep(0)

        res_b = await lm.start_log_monitoring(callback=cb_b)
        assert res_b["success"] is True
        monitor_b_id = res_b["monitor_id"]
        b_task = lm.active_monitors[monitor_b_id]["task"]

    # Let both monitor tasks drain their mocked streams
    await asyncio.wait_for(a_task, timeout=2.0)
    await asyncio.wait_for(b_task, timeout=2.0)

    # Monitor A must have seen BOTH lines — starting B did not wipe A
    assert a_entries == ["L1", "L2"], f"Monitor A saw: {a_entries}"
    # Monitor B only saw the post-start line
    assert b_entries == ["L2"], f"Monitor B saw: {b_entries}"

    # No shared `logcat -c` was ever issued
    assert not any("logcat -c" in c for c in seen_commands), (
        f"A shared logcat clear was issued: {seen_commands}"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_log_monitor_flushes_on_stop(tmp_path):
    """Regression: after start_log_monitoring writes N lines to the output
    file and we call stop_log_monitoring, the file must contain all N lines.

    This guards against the monitor task being cancelled before the final
    flush+close and against buffered writes being lost.
    """
    # Prepare 10 valid logcat lines
    expected_lines = [
        f"01-01 12:00:{i:02d}.000  123  456 I TestTag: message {i}"
        for i in range(10)
    ]

    # Queue bytes output + a sentinel empty bytes to end the stream
    stdout_queue = [line.encode("utf-8") + b"\n" for line in expected_lines]
    stdout_queue.append(b"")  # EOF sentinel — causes _monitor_logs to exit loop

    class FakeStdout:
        def __init__(self, chunks):
            self._chunks = list(chunks)

        async def readline(self):
            if not self._chunks:
                return b""
            return self._chunks.pop(0)

    class FakeProcess:
        def __init__(self, chunks):
            self.stdout = FakeStdout(chunks)
            self.pid = 99999
            self.returncode = None
            self._terminated = False

        def terminate(self):
            self._terminated = True
            self.returncode = -15

        def kill(self):
            self._terminated = True
            self.returncode = -9

        async def communicate(self):
            return (b"", b"")

        async def wait(self):
            return self.returncode or 0

    fake_proc = FakeProcess(stdout_queue)

    adb = ExtendedMockADB()
    # Use the real output_dir under tmp_path so the file ends up there
    lm = LogMonitor(adb_manager=adb, output_dir=str(tmp_path))

    async def fake_create_subprocess_exec(*args, **kwargs):
        return fake_proc

    with patch(
        "asyncio.create_subprocess_exec", side_effect=fake_create_subprocess_exec
    ):
        start_result = await lm.start_log_monitoring(
            tag_filter="TestTag",
            priority="I",
            output_file="flush_test",
        )

    assert start_result["success"] is True
    monitor_id = start_result["monitor_id"]
    output_file = Path(start_result["output_file"])

    # Give the monitor task a chance to drain the stdout queue (our fake
    # readline returns immediately; yielding to the loop lets the task run).
    for _ in range(20):
        await asyncio.sleep(0)
        if not stdout_queue:
            break

    # Stop the monitor — this should cancel the task and close the file
    stop_result = await lm.stop_log_monitoring(monitor_id=monitor_id)
    assert stop_result["success"] is True

    # Verify every line ended up in the file
    assert output_file.exists(), f"Log file {output_file} was not created"
    content = output_file.read_text(encoding="utf-8")
    file_lines = [ln for ln in content.splitlines() if ln]
    assert len(file_lines) == len(expected_lines), (
        f"Expected {len(expected_lines)} lines, got {len(file_lines)}: "
        f"{file_lines!r}"
    )
    for expected in expected_lines:
        assert expected in content, f"Missing line in output: {expected}"
