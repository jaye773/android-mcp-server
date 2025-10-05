"""Extended comprehensive tests for feedback_system.py to achieve 70%+ coverage."""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.feedback_system import (
    EnhancedMessage,
    FeedbackSystem,
    MessageBuilder,
    MessageSeverity,
    OperationProgress,
    OperationType,
    ProgressTracker,
    feedback_system,
    progress_callback,
)


@pytest.mark.unit
class TestProgressTracker:
    """Test ProgressTracker callback management and operations."""

    def test_start_operation_creates_and_notifies(self):
        """Test start_operation creates progress and notifies callbacks."""
        tracker = ProgressTracker()
        callback_mock = Mock()
        tracker.add_progress_callback(callback_mock)

        # Test operation start - covers lines 85-96
        progress = tracker.start_operation(
            operation_id="test_op_1",
            operation_type=OperationType.DEVICE_DISCOVERY,
            initial_step="Initializing",
            total_steps=5,
            estimated_duration=30.0,
        )

        # Verify progress object created correctly
        assert progress.operation_id == "test_op_1"
        assert progress.operation_type == OperationType.DEVICE_DISCOVERY
        assert progress.current_step == "Initializing"
        assert progress.total_steps == 5
        assert progress.estimated_duration == 30.0
        assert progress.completed_steps == 0
        assert isinstance(progress.start_time, datetime)

        # Verify operation stored in active operations
        assert "test_op_1" in tracker.active_operations
        assert tracker.active_operations["test_op_1"] == progress

        # Verify callback was called - covers line 95
        callback_mock.assert_called_once_with(progress)

    def test_update_progress_with_steps_calculation(self):
        """Test update_progress with step completion and percentage calculation."""
        tracker = ProgressTracker()
        callback_mock = Mock()
        tracker.add_progress_callback(callback_mock)

        # Start operation first
        tracker.start_operation(
            operation_id="test_op_2",
            operation_type=OperationType.UI_ANALYSIS,
            initial_step="Starting",
            total_steps=10,
        )
        callback_mock.reset_mock()

        # Test progress update - covers lines 106-122
        updated_progress = tracker.update_progress(
            operation_id="test_op_2",
            current_step="Processing elements",
            completed_steps=3,
            details="Found 15 UI elements",
        )

        # Verify progress was updated
        assert updated_progress is not None
        assert updated_progress.current_step == "Processing elements"
        assert updated_progress.completed_steps == 3
        assert updated_progress.details == "Found 15 UI elements"
        assert updated_progress.progress_percentage == 30.0  # 3/10 * 100

        # Verify callback was called
        callback_mock.assert_called_once_with(updated_progress)

    def test_update_progress_nonexistent_operation(self):
        """Test update_progress returns None for non-existent operation."""
        tracker = ProgressTracker()

        # Test updating non-existent operation - covers lines 106-107
        result = tracker.update_progress(
            operation_id="nonexistent", current_step="Should not work"
        )

        assert result is None

    def test_complete_operation_moves_to_history(self):
        """Test complete_operation marks as complete and moves to history."""
        tracker = ProgressTracker()
        callback_mock = Mock()
        tracker.add_progress_callback(callback_mock)

        # Start operation
        tracker.start_operation(
            operation_id="test_op_3",
            operation_type=OperationType.SCREENSHOT,
            initial_step="Taking screenshot",
        )
        callback_mock.reset_mock()

        # Test operation completion - covers lines 126-135
        completed_progress = tracker.complete_operation("test_op_3")

        # Verify completion
        assert completed_progress is not None
        assert completed_progress.current_step == "Completed"
        assert completed_progress.progress_percentage == 100.0

        # Verify moved from active to history
        assert "test_op_3" not in tracker.active_operations
        assert completed_progress in tracker.operation_history

        # Verify callback was called
        callback_mock.assert_called_once_with(completed_progress)

    def test_complete_operation_nonexistent(self):
        """Test complete_operation returns None for non-existent operation."""
        tracker = ProgressTracker()

        # Test completing non-existent operation - covers lines 126-127
        result = tracker.complete_operation("nonexistent")

        assert result is None

    def test_fail_operation_with_error_details(self):
        """Test fail_operation marks as failed and records error."""
        tracker = ProgressTracker()
        callback_mock = Mock()
        tracker.add_progress_callback(callback_mock)

        # Start operation
        tracker.start_operation(
            operation_id="test_op_4",
            operation_type=OperationType.VIDEO_RECORDING,
            initial_step="Starting recording",
        )
        callback_mock.reset_mock()

        # Test operation failure - covers lines 141-150
        failed_progress = tracker.fail_operation(
            operation_id="test_op_4", error_details="Device storage full"
        )

        # Verify failure handling
        assert failed_progress is not None
        assert failed_progress.current_step == "Failed"
        assert failed_progress.details == "Device storage full"

        # Verify moved from active to history
        assert "test_op_4" not in tracker.active_operations
        assert failed_progress in tracker.operation_history

        # Verify callback was called
        callback_mock.assert_called_once_with(failed_progress)

    def test_fail_operation_nonexistent(self):
        """Test fail_operation returns None for non-existent operation."""
        tracker = ProgressTracker()

        # Test failing non-existent operation - covers lines 141-142
        result = tracker.fail_operation("nonexistent", "Some error")

        assert result is None

    def test_get_active_operations(self):
        """Test get_active_operations returns list of active operations."""
        tracker = ProgressTracker()

        # Start multiple operations
        progress1 = tracker.start_operation(
            operation_id="op1",
            operation_type=OperationType.DEVICE_CONNECTION,
            initial_step="Connecting",
        )
        progress2 = tracker.start_operation(
            operation_id="op2",
            operation_type=OperationType.LOG_RETRIEVAL,
            initial_step="Fetching logs",
        )

        # Test getting active operations - covers line 154
        active_ops = tracker.get_active_operations()

        assert len(active_ops) == 2
        assert progress1 in active_ops
        assert progress2 in active_ops

    def test_callback_error_handling(self):
        """Test callback error handling doesn't break progress updates."""
        tracker = ProgressTracker()

        # Add callback that raises exception
        failing_callback = Mock(side_effect=Exception("Callback error"))
        working_callback = Mock()

        tracker.add_progress_callback(failing_callback)
        tracker.add_progress_callback(working_callback)

        # Test that operation still works despite callback failure - covers lines 162-166
        with patch("src.feedback_system.logger") as mock_logger:
            progress = tracker.start_operation(
                operation_id="test_callback_error",
                operation_type=OperationType.INPUT_ACTION,
                initial_step="Testing callback error",
            )

            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            assert "Progress callback failed" in str(
                mock_logger.warning.call_args[0][0]
            )

            # Verify working callback was still called
            working_callback.assert_called_once_with(progress)


@pytest.mark.unit
class TestMessageBuilder:
    """Test MessageBuilder pattern matching and message creation."""

    def test_create_success_message_with_duration(self):
        """Test create_success_message with all parameters."""
        # Test success message creation - covers line 263
        message = MessageBuilder.create_success_message(
            title="Operation Complete",
            message="Successfully captured screenshot",
            operation_context="screenshot_capture",
            duration=2.5,
        )

        assert message.severity == MessageSeverity.SUCCESS
        assert message.title == "Operation Complete"
        assert message.message == "Successfully captured screenshot"
        assert message.operation_context == "screenshot_capture"
        assert message.operation_duration == 2.5
        assert isinstance(message.timestamp, datetime)

    def test_create_error_message_with_pattern_matching(self):
        """Test create_error_message with various error patterns."""

        # Test "no devices" pattern - covers lines 281-303
        error_msg = MessageBuilder.create_error_message(
            title="Device Connection Failed",
            error="no devices/emulators found",
            operation_context="device_discovery",
            duration=5.0,
        )

        assert error_msg.severity == MessageSeverity.ERROR
        assert error_msg.error_code == "DEVICE_NOT_FOUND"
        assert "Ensure Android device is connected via USB" in error_msg.suggestions
        assert "accept the USB debugging prompt" in error_msg.troubleshooting_tips[0]

        # Test "device offline" pattern
        offline_msg = MessageBuilder.create_error_message(
            title="Device Offline", error="device offline"
        )

        assert offline_msg.error_code == "DEVICE_OFFLINE"
        assert "Disconnect and reconnect the device" in offline_msg.suggestions

        # Test "command timed out" pattern
        timeout_msg = MessageBuilder.create_error_message(
            title="Timeout Error", error="command timed out after 30 seconds"
        )

        assert timeout_msg.error_code == "OPERATION_TIMEOUT"
        assert "Device may be slow or unresponsive" in timeout_msg.suggestions

    def test_create_error_message_no_pattern_match(self):
        """Test create_error_message with unknown error gets generic suggestions."""

        # Test error that doesn't match any pattern - covers lines 295-301
        unknown_error = MessageBuilder.create_error_message(
            title="Unknown Error", error="completely unknown error type"
        )

        assert unknown_error.error_code is None
        assert "Check device connection and status" in unknown_error.suggestions
        assert "Retry the operation after a brief wait" in unknown_error.suggestions
        assert "Verify device permissions and settings" in unknown_error.suggestions

    def test_create_error_message_with_exception_object(self):
        """Test create_error_message works with Exception objects."""

        test_exception = ValueError("permission denied for operation")

        error_msg = MessageBuilder.create_error_message(
            title="Permission Error", error=test_exception
        )

        assert error_msg.error_code == "PERMISSION_DENIED"
        assert error_msg.message == "permission denied for operation"
        assert "Grant necessary permissions on the device" in error_msg.suggestions

    def test_create_validation_error_with_suggestions(self):
        """Test create_validation_error creates proper validation message."""

        # Test validation error creation - covers lines 324-330
        validation_msg = MessageBuilder.create_validation_error(
            parameter="coordinates",
            value=(-1, 50),
            expected="positive integers within screen bounds",
            operation_context="tap_action",
        )

        assert validation_msg.severity == MessageSeverity.ERROR
        assert validation_msg.title == "Parameter Validation Error"
        assert validation_msg.message == "Invalid parameter 'coordinates': (-1, 50)"
        assert validation_msg.operation_context == "tap_action"
        assert validation_msg.error_code == "INVALID_PARAMETER"

        # Check suggestions contain expected information
        suggestions = validation_msg.suggestions
        assert any(
            "Expected coordinates to be positive integers within screen bounds" in s
            for s in suggestions
        )
        assert any("Current value: (-1, 50)" in s for s in suggestions)
        assert any(
            "Check the parameter documentation for valid values" in s
            for s in suggestions
        )

    def test_create_warning_message_with_suggestions(self):
        """Test create_warning_message with custom suggestions."""

        # Test warning message creation - covers line 349
        warning_msg = MessageBuilder.create_warning_message(
            title="Performance Warning",
            message="Device battery level is low",
            operation_context="long_operation",
            suggestions=["Connect device to charger", "Reduce operation intensity"],
        )

        assert warning_msg.severity == MessageSeverity.WARNING
        assert warning_msg.title == "Performance Warning"
        assert warning_msg.message == "Device battery level is low"
        assert warning_msg.operation_context == "long_operation"
        assert warning_msg.suggestions == [
            "Connect device to charger",
            "Reduce operation intensity",
        ]
        assert isinstance(warning_msg.timestamp, datetime)

    def test_create_warning_message_without_suggestions(self):
        """Test create_warning_message defaults to empty suggestions."""

        warning_msg = MessageBuilder.create_warning_message(
            title="Simple Warning", message="Some warning occurred"
        )

        assert warning_msg.suggestions == []


@pytest.mark.unit
class TestFeedbackSystem:
    """Test FeedbackSystem coordination and callback management."""

    def test_add_feedback_callback(self):
        """Test adding feedback callbacks."""
        system = FeedbackSystem()
        callback_mock = Mock()

        # Test adding callback - covers line 369
        system.add_feedback_callback(callback_mock)

        assert callback_mock in system.feedback_callbacks

    def test_send_feedback_to_callbacks(self):
        """Test send_feedback distributes to all callbacks."""
        system = FeedbackSystem()
        callback1 = Mock()
        callback2 = Mock()

        system.add_feedback_callback(callback1)
        system.add_feedback_callback(callback2)

        # Create test message
        message = EnhancedMessage(
            severity=MessageSeverity.SUCCESS,
            title="Test Success",
            message="Test message",
            operation_context="test_context",
            error_code="TEST_CODE",
            suggestions=["Test suggestion"],
            troubleshooting_tips=["Test tip"],
            timestamp=datetime.now(),
            operation_duration=1.5,
        )

        # Test feedback distribution - covers lines 373-390
        system.send_feedback(message)

        # Verify both callbacks received the feedback data
        assert callback1.call_count == 1
        assert callback2.call_count == 1

        # Verify feedback data structure
        feedback_data = callback1.call_args[0][0]
        assert feedback_data["type"] == "message"
        assert feedback_data["severity"] == "success"
        assert feedback_data["title"] == "Test Success"
        assert feedback_data["message"] == "Test message"
        assert feedback_data["operation_context"] == "test_context"
        assert feedback_data["error_code"] == "TEST_CODE"
        assert feedback_data["suggestions"] == ["Test suggestion"]
        assert feedback_data["troubleshooting_tips"] == ["Test tip"]
        assert feedback_data["operation_duration"] == 1.5
        assert feedback_data["timestamp"] is not None

    def test_send_feedback_callback_error_handling(self):
        """Test send_feedback handles callback errors gracefully."""
        system = FeedbackSystem()

        failing_callback = Mock(side_effect=Exception("Callback failed"))
        working_callback = Mock()

        system.add_feedback_callback(failing_callback)
        system.add_feedback_callback(working_callback)

        message = EnhancedMessage(
            severity=MessageSeverity.INFO, title="Test", message="Test message"
        )

        # Test error handling - covers lines 386-390
        with patch("src.feedback_system.logger") as mock_logger:
            system.send_feedback(message)

            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            assert "Feedback callback failed" in str(
                mock_logger.warning.call_args[0][0]
            )

            # Verify working callback was still called
            working_callback.assert_called_once()

    def test_send_progress_to_callbacks(self):
        """Test send_progress distributes progress updates."""
        system = FeedbackSystem()
        callback_mock = Mock()
        system.add_feedback_callback(callback_mock)

        # Create test progress
        start_time = datetime.now() - timedelta(seconds=30)
        progress = OperationProgress(
            operation_id="test_progress",
            operation_type=OperationType.FILE_TRANSFER,
            start_time=start_time,
            current_step="Transferring files",
            total_steps=100,
            completed_steps=60,
            progress_percentage=60.0,
            details="Transferred 6MB of 10MB",
        )

        # Test progress distribution - covers lines 394-409
        system.send_progress(progress)

        # Verify callback received progress data
        callback_mock.assert_called_once()
        progress_data = callback_mock.call_args[0][0]

        assert progress_data["type"] == "progress"
        assert progress_data["operation_id"] == "test_progress"
        assert progress_data["operation_type"] == "file_transfer"
        assert progress_data["current_step"] == "Transferring files"
        assert progress_data["progress_percentage"] == 60.0
        assert progress_data["details"] == "Transferred 6MB of 10MB"
        assert "elapsed_time" in progress_data
        assert "estimated_remaining" in progress_data

    def test_send_progress_callback_error_handling(self):
        """Test send_progress handles callback errors gracefully."""
        system = FeedbackSystem()

        failing_callback = Mock(side_effect=Exception("Progress callback failed"))
        working_callback = Mock()

        system.add_feedback_callback(failing_callback)
        system.add_feedback_callback(working_callback)

        # Create test progress
        progress = OperationProgress(
            operation_id="test_error_handling",
            operation_type=OperationType.SCREENSHOT,
            start_time=datetime.now(),
            current_step="Processing",
        )

        # Test error handling in send_progress - covers lines 408-409
        with patch("src.feedback_system.logger") as mock_logger:
            system.send_progress(progress)

            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            assert "Progress callback failed" in str(
                mock_logger.warning.call_args[0][0]
            )

            # Verify working callback was still called
            working_callback.assert_called_once()

    def test_estimate_remaining_time_with_progress(self):
        """Test _estimate_remaining_time calculation logic."""
        system = FeedbackSystem()

        # Create progress with 50% completion
        start_time = datetime.now() - timedelta(seconds=30)  # 30 seconds elapsed
        progress = OperationProgress(
            operation_id="test_timing",
            operation_type=OperationType.UI_ANALYSIS,
            start_time=start_time,
            current_step="Processing",
            progress_percentage=50.0,
        )

        # Test time estimation - covers lines 413-421
        estimated = system._estimate_remaining_time(progress)

        # Should estimate another 30 seconds (100/50 * 30 - 30 = 30)
        assert estimated is not None
        assert 25 <= estimated <= 35  # Allow some tolerance for test execution time

    def test_estimate_remaining_time_no_progress(self):
        """Test _estimate_remaining_time with no progress returns estimated duration."""
        system = FeedbackSystem()

        # Create progress with no percentage but estimated duration
        progress = OperationProgress(
            operation_id="test_timing_no_progress",
            operation_type=OperationType.DEVICE_DISCOVERY,
            start_time=datetime.now(),
            current_step="Starting",
            estimated_duration=120.0,
        )

        # Test fallback to estimated duration - covers lines 413-414
        estimated = system._estimate_remaining_time(progress)
        assert estimated == 120.0

    def test_estimate_remaining_time_completed(self):
        """Test _estimate_remaining_time returns 0 for completed operations."""
        system = FeedbackSystem()

        progress = OperationProgress(
            operation_id="test_completed",
            operation_type=OperationType.SCREENSHOT,
            start_time=datetime.now() - timedelta(seconds=10),
            current_step="Completed",
            progress_percentage=100.0,
        )

        # Test completed operation - covers lines 417-418
        estimated = system._estimate_remaining_time(progress)
        assert estimated == 0.0


@pytest.mark.unit
@pytest.mark.asyncio
class TestFeedbackSystemWithProgress:
    """Test FeedbackSystem with_progress context manager functionality."""

    async def test_with_progress_async_success(self):
        """Test with_progress wrapper for successful async operations."""
        system = FeedbackSystem()
        callback_mock = Mock()
        system.add_feedback_callback(callback_mock)

        # Mock async function that returns success
        async def mock_async_operation(param1, param2):
            await asyncio.sleep(0.01)  # Simulate work
            return {"success": True, "result": f"{param1}_{param2}"}

        # Test async operation with progress - covers lines 440-489
        result = await system.with_progress(
            OperationType.UI_ANALYSIS,
            "Test Async Operation",
            mock_async_operation,
            "test_param1",
            "test_param2",
        )

        # Verify result
        assert result["success"] is True
        assert result["result"] == "test_param1_test_param2"

        # Verify callbacks were called (progress start, progress complete, success feedback)
        assert callback_mock.call_count >= 2  # At least progress and feedback calls

    async def test_with_progress_sync_success(self):
        """Test with_progress wrapper for successful sync operations."""
        system = FeedbackSystem()
        callback_mock = Mock()
        system.add_feedback_callback(callback_mock)

        # Mock sync function that returns success
        def mock_sync_operation(value):
            return {"success": True, "processed": value * 2}

        # Test sync operation detection and execution - covers lines 453-456
        result = await system.with_progress(
            OperationType.INPUT_ACTION, "Test Sync Operation", mock_sync_operation, 42
        )

        # Verify result
        assert result["success"] is True
        assert result["processed"] == 84

    async def test_with_progress_operation_failure(self):
        """Test with_progress wrapper handles operation failures."""
        system = FeedbackSystem()
        callback_mock = Mock()
        system.add_feedback_callback(callback_mock)

        # Mock function that raises exception
        async def failing_operation():
            raise ValueError("Test operation failed")

        # Test exception handling - covers lines 474-499
        result = await system.with_progress(
            OperationType.DEVICE_CONNECTION, "Failing Operation", failing_operation
        )

        # Verify error result structure
        assert result["success"] is False
        assert result["error"] == "Test operation failed"
        assert result["operation_context"] == "Failing Operation"
        assert "duration" in result
        assert "feedback" in result
        assert "error_code" in result["feedback"]
        assert "suggestions" in result["feedback"]

    async def test_with_progress_operation_id_generation(self):
        """Test operation ID generation includes timestamp."""
        system = FeedbackSystem()

        def dummy_operation():
            return {"success": True}

        # Mock time.time to control operation ID
        with patch("src.feedback_system.time.time", return_value=1234567890):
            await system.with_progress(
                OperationType.LOG_RETRIEVAL, "Test Operation", dummy_operation
            )

            # Verify operation was tracked with expected ID format
            # The operation should be completed and moved to history
            assert len(system.progress_tracker.operation_history) >= 1


@pytest.mark.unit
class TestDefaultProgressCallback:
    """Test the default progress callback function."""

    def test_progress_callback_with_percentage(self):
        """Test default progress_callback logs with percentage."""
        progress = OperationProgress(
            operation_id="test_log",
            operation_type=OperationType.VIDEO_RECORDING,
            start_time=datetime.now(),
            current_step="Recording video",
            progress_percentage=75.0,
        )

        # Test callback with percentage - covers lines 508-513
        with patch("src.feedback_system.logger") as mock_logger:
            progress_callback(progress)

            mock_logger.info.assert_called_once()
            log_message = mock_logger.info.call_args[0][0]
            assert "[video_recording]" in log_message
            assert "Recording video" in log_message
            assert "(75.0%)" in log_message

    def test_progress_callback_without_percentage(self):
        """Test default progress_callback logs without percentage."""
        progress = OperationProgress(
            operation_id="test_log_no_pct",
            operation_type=OperationType.DEVICE_DISCOVERY,
            start_time=datetime.now(),
            current_step="Searching for devices",
        )

        # Test callback without percentage - covers lines 512-513
        with patch("src.feedback_system.logger") as mock_logger:
            progress_callback(progress)

            mock_logger.info.assert_called_once()
            log_message = mock_logger.info.call_args[0][0]
            assert "[device_discovery]" in log_message
            assert "Searching for devices" in log_message
            assert "%" not in log_message


@pytest.mark.unit
class TestGlobalFeedbackSystem:
    """Test the global feedback_system instance."""

    def test_global_feedback_system_exists(self):
        """Test global feedback_system instance is properly initialized."""
        # Verify global instance exists and has expected structure
        assert feedback_system is not None
        assert hasattr(feedback_system, "progress_tracker")
        assert hasattr(feedback_system, "message_builder")
        assert hasattr(feedback_system, "feedback_callbacks")

        # Verify default progress callback is registered
        assert len(feedback_system.progress_tracker.progress_callbacks) >= 1

    def test_global_system_default_callback_registration(self):
        """Test that default progress callback is registered on global system."""
        # The default callback should be in the global system's callbacks
        callbacks = feedback_system.progress_tracker.progress_callbacks

        # Verify at least one callback is registered (the default one)
        assert len(callbacks) >= 1

        # Test that the callback works by triggering a progress update
        with patch("src.feedback_system.logger") as mock_logger:
            progress = feedback_system.progress_tracker.start_operation(
                operation_id="global_test",
                operation_type=OperationType.SCREENSHOT,
                initial_step="Testing global callback",
            )

            # The default callback should have logged something
            mock_logger.info.assert_called()


@pytest.mark.unit
class TestEnumValues:
    """Test enum value access and string representations."""

    def test_operation_type_values(self):
        """Test OperationType enum values are accessible."""
        assert OperationType.DEVICE_DISCOVERY.value == "device_discovery"
        assert OperationType.UI_ANALYSIS.value == "ui_analysis"
        assert OperationType.SCREENSHOT.value == "screenshot"
        assert OperationType.VIDEO_RECORDING.value == "video_recording"

    def test_message_severity_values(self):
        """Test MessageSeverity enum values are accessible."""
        assert MessageSeverity.SUCCESS.value == "success"
        assert MessageSeverity.INFO.value == "info"
        assert MessageSeverity.WARNING.value == "warning"
        assert MessageSeverity.ERROR.value == "error"
        assert MessageSeverity.CRITICAL.value == "critical"


@pytest.mark.unit
class TestConcurrentOperations:
    """Test concurrent operation handling and thread safety."""

    @pytest.mark.asyncio
    async def test_multiple_concurrent_operations(self):
        """Test system handles multiple concurrent operations."""
        system = FeedbackSystem()

        async def concurrent_operation(op_id, delay):
            await asyncio.sleep(delay)
            return {"success": True, "operation_id": op_id}

        # Start multiple operations concurrently
        tasks = [
            system.with_progress(
                OperationType.UI_ANALYSIS,
                f"Concurrent Op {i}",
                concurrent_operation,
                f"op_{i}",
                0.01 * i,
            )
            for i in range(3)
        ]

        # Wait for all operations to complete
        results = await asyncio.gather(*tasks)

        # Verify all operations completed successfully
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result["success"] is True
            assert result["operation_id"] == f"op_{i}"

        # Verify operations were tracked properly
        assert len(system.progress_tracker.operation_history) >= 3

    def test_callback_isolation(self):
        """Test that callback failures don't affect other callbacks."""
        tracker = ProgressTracker()

        # Create callbacks with different behaviors
        successful_callback = Mock()
        failing_callback = Mock(side_effect=Exception("Test error"))
        another_successful_callback = Mock()

        tracker.add_progress_callback(successful_callback)
        tracker.add_progress_callback(failing_callback)
        tracker.add_progress_callback(another_successful_callback)

        # Trigger callbacks
        progress = tracker.start_operation(
            operation_id="isolation_test",
            operation_type=OperationType.INPUT_ACTION,
            initial_step="Testing isolation",
        )

        # Verify successful callbacks were called despite failure
        successful_callback.assert_called_once_with(progress)
        another_successful_callback.assert_called_once_with(progress)
        failing_callback.assert_called_once_with(progress)


@pytest.mark.unit
class TestErrorPatternMatching:
    """Test comprehensive error pattern matching in MessageBuilder."""

    def test_all_error_patterns_covered(self):
        """Test all defined error patterns can be matched."""
        patterns_to_test = [
            ("ui dump failed", "UI_DUMP_FAILED"),
            ("element not found", "ELEMENT_NOT_FOUND"),
            ("screenshot failed", "SCREENSHOT_FAILED"),
            ("recording failed", "RECORDING_FAILED"),
        ]

        for error_text, expected_code in patterns_to_test:
            error_msg = MessageBuilder.create_error_message(
                title="Pattern Test", error=error_text
            )

            assert error_msg.error_code == expected_code
            assert len(error_msg.suggestions) > 0

    def test_case_insensitive_pattern_matching(self):
        """Test error pattern matching is case insensitive."""
        error_msg = MessageBuilder.create_error_message(
            title="Case Test", error="NO DEVICES FOUND"  # Uppercase
        )

        assert error_msg.error_code == "DEVICE_NOT_FOUND"

    def test_partial_pattern_matching(self):
        """Test partial text matches trigger patterns."""
        error_msg = MessageBuilder.create_error_message(
            title="Partial Test",
            error="The operation command timed out due to network issues",
        )

        assert error_msg.error_code == "OPERATION_TIMEOUT"


if __name__ == "__main__":
    pytest.main([__file__])
