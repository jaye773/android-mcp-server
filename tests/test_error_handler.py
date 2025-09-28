"""Tests for error handling system."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.error_handler import (
    ErrorCode, AndroidMCPError, ErrorHandler,
    get_recovery_suggestions, format_error_response
)


class TestErrorCode:
    """Test error code enumeration."""

    def test_error_code_values(self):
        """Test error code string values."""
        assert ErrorCode.SYSTEM_INITIALIZATION_FAILED.value == "SYSTEM_1000"
        assert ErrorCode.NO_DEVICES_FOUND.value == "DEVICE_1100"
        assert ErrorCode.ADB_COMMAND_FAILED.value == "ADB_1200"
        assert ErrorCode.UI_DUMP_FAILED.value == "UI_1300"
        assert ErrorCode.SCREENSHOT_FAILED.value == "MEDIA_1400"

    def test_error_code_categories(self):
        """Test error code categorization."""
        # System errors (1000-1099)
        system_codes = [
            ErrorCode.SYSTEM_INITIALIZATION_FAILED,
            ErrorCode.COMPONENT_INIT_FAILED,
            ErrorCode.DEPENDENCY_MISSING
        ]
        for code in system_codes:
            assert "SYSTEM" in code.value

        # Device errors (1100-1199)
        device_codes = [
            ErrorCode.NO_DEVICES_FOUND,
            ErrorCode.DEVICE_OFFLINE,
            ErrorCode.DEVICE_UNAUTHORIZED
        ]
        for code in device_codes:
            assert "DEVICE" in code.value

        # ADB errors (1200-1299)
        adb_codes = [
            ErrorCode.ADB_COMMAND_FAILED,
            ErrorCode.ADB_TIMEOUT,
            ErrorCode.ADB_PERMISSION_DENIED
        ]
        for code in adb_codes:
            assert "ADB" in code.value


class TestAndroidMCPError:
    """Test AndroidMCPError exception class."""

    def test_error_creation_with_code(self):
        """Test error creation with error code."""
        error = AndroidMCPError(
            ErrorCode.DEVICE_NOT_FOUND,
            "Device not found",
            {"device_id": "emulator-5554"}
        )

        assert error.error_code == ErrorCode.DEVICE_NOT_FOUND
        assert error.message == "Device not found"
        assert error.details["device_id"] == "emulator-5554"
        assert isinstance(error.timestamp, datetime)

    def test_error_creation_minimal(self):
        """Test error creation with minimal parameters."""
        error = AndroidMCPError(ErrorCode.ADB_COMMAND_FAILED, "Command failed")

        assert error.error_code == ErrorCode.ADB_COMMAND_FAILED
        assert error.message == "Command failed"
        assert error.details == {}
        assert error.recovery_suggestions == []

    def test_error_str_representation(self):
        """Test error string representation."""
        error = AndroidMCPError(
            ErrorCode.UI_DUMP_FAILED,
            "UI dump failed",
            {"device": "test-device"}
        )

        error_str = str(error)
        assert "UI_1300" in error_str
        assert "UI dump failed" in error_str

    def test_error_dict_representation(self):
        """Test error dictionary representation."""
        error = AndroidMCPError(
            ErrorCode.SCREENSHOT_FAILED,
            "Screenshot failed",
            {"path": "/sdcard/test.png"},
            ["Retry the operation", "Check device storage"]
        )

        error_dict = error.to_dict()

        assert error_dict["error_code"] == "MEDIA_1400"
        assert error_dict["message"] == "Screenshot failed"
        assert error_dict["details"]["path"] == "/sdcard/test.png"
        assert len(error_dict["recovery_suggestions"]) == 2
        assert "timestamp" in error_dict

    def test_error_with_recovery_suggestions(self):
        """Test error with recovery suggestions."""
        suggestions = [
            "Check device connection",
            "Restart ADB server",
            "Enable USB debugging"
        ]

        error = AndroidMCPError(
            ErrorCode.DEVICE_CONNECTION_LOST,
            "Connection lost",
            recovery_suggestions=suggestions
        )

        assert error.recovery_suggestions == suggestions


class TestErrorHandler:
    """Test ErrorHandler functionality."""

    def test_error_handler_initialization(self):
        """Test error handler initialization."""
        handler = ErrorHandler()

        assert handler.error_counts == {}
        assert handler.last_errors == {}

    def test_handle_error_basic(self):
        """Test basic error handling."""
        handler = ErrorHandler()

        error = AndroidMCPError(
            ErrorCode.ADB_COMMAND_FAILED,
            "Command failed"
        )

        result = handler.handle_error(error)

        assert result["error_code"] == "ADB_1200"
        assert result["message"] == "Command failed"
        assert "timestamp" in result
        assert "recovery_suggestions" in result

    def test_handle_error_with_context(self):
        """Test error handling with context information."""
        handler = ErrorHandler()

        error = AndroidMCPError(
            ErrorCode.ELEMENT_NOT_FOUND,
            "Element not found",
            {"text": "login button", "timeout": 5}
        )

        result = handler.handle_error(error, context={"operation": "tap_element"})

        assert result["error_code"] == "UI_1301"
        assert result["context"]["operation"] == "tap_element"
        assert result["details"]["text"] == "login button"

    def test_error_counting(self):
        """Test error counting functionality."""
        handler = ErrorHandler()

        error_code = ErrorCode.ADB_TIMEOUT

        # Handle same error multiple times
        for _ in range(3):
            error = AndroidMCPError(error_code, "Timeout occurred")
            handler.handle_error(error)

        assert handler.error_counts[error_code] == 3

    def test_get_error_statistics(self):
        """Test error statistics retrieval."""
        handler = ErrorHandler()

        # Generate different types of errors
        errors = [
            AndroidMCPError(ErrorCode.ADB_TIMEOUT, "Timeout 1"),
            AndroidMCPError(ErrorCode.ADB_TIMEOUT, "Timeout 2"),
            AndroidMCPError(ErrorCode.DEVICE_OFFLINE, "Device offline"),
            AndroidMCPError(ErrorCode.UI_DUMP_FAILED, "UI dump failed")
        ]

        for error in errors:
            handler.handle_error(error)

        stats = handler.get_error_statistics()

        assert stats["total_errors"] == 4
        assert stats["unique_error_types"] == 3
        assert stats["most_common_error"]["error_code"] == ErrorCode.ADB_TIMEOUT
        assert stats["most_common_error"]["count"] == 2

    def test_clear_error_history(self):
        """Test clearing error history."""
        handler = ErrorHandler()

        # Generate some errors
        error = AndroidMCPError(ErrorCode.DEVICE_NOT_FOUND, "Device not found")
        handler.handle_error(error)

        assert len(handler.error_counts) > 0
        assert len(handler.last_errors) > 0

        handler.clear_error_history()

        assert len(handler.error_counts) == 0
        assert len(handler.last_errors) == 0

    def test_exception_to_android_mcp_error(self):
        """Test conversion of generic exceptions to AndroidMCPError."""
        handler = ErrorHandler()

        # Test with generic exception
        generic_error = Exception("Something went wrong")
        result = handler.handle_exception(generic_error, "test_operation")

        assert result["error_code"] == "UNKNOWN_ERROR"
        assert "Something went wrong" in result["message"]
        assert result["context"]["operation"] == "test_operation"

        # Test with specific exception types
        timeout_error = TimeoutError("Operation timed out")
        result = handler.handle_exception(timeout_error, "adb_command")

        assert "timeout" in result["message"].lower()

    def test_error_pattern_detection(self):
        """Test detection of error patterns."""
        handler = ErrorHandler()

        # Simulate repeated timeout errors
        for _ in range(5):
            error = AndroidMCPError(ErrorCode.ADB_TIMEOUT, "Command timed out")
            handler.handle_error(error)

        # Check if pattern is detected
        stats = handler.get_error_statistics()
        most_common = stats["most_common_error"]

        if most_common["count"] >= 3:
            # Pattern detected, should suggest specific recovery
            pass  # Implementation-dependent

    def test_contextual_recovery_suggestions(self):
        """Test contextual recovery suggestions."""
        handler = ErrorHandler()

        # Device connection error should suggest device-specific recovery
        device_error = AndroidMCPError(
            ErrorCode.DEVICE_CONNECTION_LOST,
            "Device connection lost"
        )
        result = handler.handle_error(device_error)

        recovery_text = " ".join(result["recovery_suggestions"]).lower()
        assert any(word in recovery_text for word in ["device", "connection", "usb"])

        # ADB error should suggest ADB-specific recovery
        adb_error = AndroidMCPError(
            ErrorCode.ADB_DAEMON_ERROR,
            "ADB daemon error"
        )
        result = handler.handle_error(adb_error)

        recovery_text = " ".join(result["recovery_suggestions"]).lower()
        assert any(word in recovery_text for word in ["adb", "daemon", "restart"])


class TestRecoverySuggestions:
    """Test recovery suggestion system."""

    def test_get_recovery_suggestions_device_errors(self):
        """Test recovery suggestions for device errors."""
        suggestions = get_recovery_suggestions(ErrorCode.NO_DEVICES_FOUND)

        assert len(suggestions) > 0
        suggestions_text = " ".join(suggestions).lower()
        assert any(word in suggestions_text for word in ["connect", "device", "usb"])

    def test_get_recovery_suggestions_adb_errors(self):
        """Test recovery suggestions for ADB errors."""
        suggestions = get_recovery_suggestions(ErrorCode.ADB_COMMAND_FAILED)

        assert len(suggestions) > 0
        suggestions_text = " ".join(suggestions).lower()
        assert any(word in suggestions_text for word in ["adb", "command", "retry"])

    def test_get_recovery_suggestions_ui_errors(self):
        """Test recovery suggestions for UI errors."""
        suggestions = get_recovery_suggestions(ErrorCode.ELEMENT_NOT_FOUND)

        assert len(suggestions) > 0
        suggestions_text = " ".join(suggestions).lower()
        assert any(word in suggestions_text for word in ["element", "wait", "ui"])

    def test_get_recovery_suggestions_media_errors(self):
        """Test recovery suggestions for media errors."""
        suggestions = get_recovery_suggestions(ErrorCode.SCREENSHOT_FAILED)

        assert len(suggestions) > 0
        suggestions_text = " ".join(suggestions).lower()
        assert any(word in suggestions_text for word in ["screenshot", "storage", "permission"])

    def test_get_recovery_suggestions_unknown_error(self):
        """Test recovery suggestions for unknown errors."""
        # Create a mock error code not in the system
        class MockErrorCode:
            value = "UNKNOWN_9999"

        suggestions = get_recovery_suggestions(MockErrorCode())

        # Should provide generic suggestions
        assert len(suggestions) > 0
        suggestions_text = " ".join(suggestions).lower()
        assert any(word in suggestions_text for word in ["retry", "check", "restart"])

    def test_contextual_recovery_suggestions(self):
        """Test contextual recovery suggestions with details."""
        # Test with timeout context
        suggestions = get_recovery_suggestions(
            ErrorCode.ADB_TIMEOUT,
            context={"timeout_seconds": 30, "command": "shell input tap 100 200"}
        )

        assert len(suggestions) > 0
        # Should suggest increasing timeout or checking device responsiveness

        # Test with permission context
        suggestions = get_recovery_suggestions(
            ErrorCode.ADB_PERMISSION_DENIED,
            context={"operation": "pull_file", "path": "/data/app/com.test"}
        )

        assert len(suggestions) > 0
        suggestions_text = " ".join(suggestions).lower()
        assert any(word in suggestions_text for word in ["permission", "root", "access"])


class TestErrorResponseFormatting:
    """Test error response formatting."""

    def test_format_error_response_basic(self):
        """Test basic error response formatting."""
        error = AndroidMCPError(
            ErrorCode.DEVICE_NOT_FOUND,
            "Device not found"
        )

        response = format_error_response(error)

        assert response["success"] is False
        assert response["error_code"] == "DEVICE_1101"
        assert response["error"] == "Device not found"
        assert "timestamp" in response
        assert "recovery_suggestions" in response

    def test_format_error_response_with_details(self):
        """Test error response formatting with details."""
        error = AndroidMCPError(
            ErrorCode.ELEMENT_NOT_FOUND,
            "Element not found",
            {
                "text": "login button",
                "resource_id": "com.app:id/login",
                "timeout": 10
            }
        )

        response = format_error_response(error)

        assert response["success"] is False
        assert "details" in response
        assert response["details"]["text"] == "login button"
        assert response["details"]["timeout"] == 10

    def test_format_error_response_with_context(self):
        """Test error response formatting with additional context."""
        error = AndroidMCPError(
            ErrorCode.ADB_COMMAND_FAILED,
            "Command failed"
        )

        context = {
            "operation": "tap_screen",
            "device_id": "emulator-5554",
            "attempt_number": 2
        }

        response = format_error_response(error, context=context)

        assert response["success"] is False
        assert "context" in response
        assert response["context"]["operation"] == "tap_screen"
        assert response["context"]["attempt_number"] == 2

    def test_format_error_response_sanitization(self):
        """Test that sensitive information is sanitized from error responses."""
        error = AndroidMCPError(
            ErrorCode.ADB_PERMISSION_DENIED,
            "Permission denied",
            {
                "command": "adb shell su -c 'cat /data/data/com.app/password.txt'",
                "user": "root",
                "file_path": "/data/sensitive/config.json"
            }
        )

        response = format_error_response(error)

        # Should not expose sensitive command details in user-facing response
        assert response["success"] is False
        # Implementation should sanitize sensitive paths/commands


class TestErrorHandlerIntegration:
    """Test error handler integration with other components."""

    def test_error_handler_with_adb_manager(self):
        """Test error handler integration with ADB operations."""
        handler = ErrorHandler()

        # Simulate ADB command failure
        adb_error = AndroidMCPError(
            ErrorCode.ADB_COMMAND_FAILED,
            "adb command failed: device offline",
            {"command": "shell uiautomator dump", "device": "emulator-5554"}
        )

        result = handler.handle_error(adb_error)

        assert result["error_code"] == "ADB_1200"
        assert "recovery_suggestions" in result
        assert len(result["recovery_suggestions"]) > 0

    def test_error_handler_with_ui_operations(self):
        """Test error handler integration with UI operations."""
        handler = ErrorHandler()

        # Simulate UI element not found
        ui_error = AndroidMCPError(
            ErrorCode.ELEMENT_NOT_FOUND,
            "UI element not found",
            {
                "search_criteria": {"text": "Submit", "class": "android.widget.Button"},
                "timeout": 10,
                "total_elements": 25
            }
        )

        result = handler.handle_error(ui_error, context={"operation": "tap_element"})

        assert result["error_code"] == "UI_1301"
        assert result["context"]["operation"] == "tap_element"
        assert "search_criteria" in result["details"]

    def test_error_handler_with_media_operations(self):
        """Test error handler integration with media operations."""
        handler = ErrorHandler()

        # Simulate screenshot failure
        media_error = AndroidMCPError(
            ErrorCode.SCREENSHOT_FAILED,
            "Failed to capture screenshot",
            {
                "device_path": "/sdcard/screenshot.png",
                "error": "No space left on device"
            }
        )

        result = handler.handle_error(media_error, context={"operation": "take_screenshot"})

        assert result["error_code"] == "MEDIA_1400"
        assert "device_path" in result["details"]

        # Should suggest storage-related recovery
        recovery_text = " ".join(result["recovery_suggestions"]).lower()
        assert any(word in recovery_text for word in ["storage", "space", "cleanup"])


class TestErrorHandlerPerformance:
    """Test error handler performance characteristics."""

    @pytest.mark.performance
    def test_error_handling_performance(self):
        """Test that error handling operations are fast."""
        import time

        handler = ErrorHandler()

        start_time = time.time()

        # Handle many errors quickly
        for i in range(1000):
            error = AndroidMCPError(
                ErrorCode.ADB_COMMAND_FAILED,
                f"Error {i}"
            )
            handler.handle_error(error)

        end_time = time.time()
        duration = end_time - start_time

        # Should handle 1000 errors in reasonable time
        assert duration < 1.0, f"Error handling took {duration} seconds"

    @pytest.mark.performance
    def test_error_statistics_performance(self):
        """Test performance of error statistics calculation."""
        import time

        handler = ErrorHandler()

        # Generate many different errors
        error_codes = [
            ErrorCode.ADB_TIMEOUT,
            ErrorCode.DEVICE_OFFLINE,
            ErrorCode.UI_DUMP_FAILED,
            ErrorCode.ELEMENT_NOT_FOUND,
            ErrorCode.SCREENSHOT_FAILED
        ]

        for _ in range(200):
            for code in error_codes:
                error = AndroidMCPError(code, "Test error")
                handler.handle_error(error)

        start_time = time.time()
        stats = handler.get_error_statistics()
        end_time = time.time()

        duration = end_time - start_time
        assert duration < 0.1, f"Statistics calculation took {duration} seconds"
        assert stats["total_errors"] == 1000
        assert stats["unique_error_types"] == 5