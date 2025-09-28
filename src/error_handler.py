"""Comprehensive error handling system for Android MCP Server."""

import logging
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class ErrorCode(Enum):
    """Standardized error codes for the Android MCP Server."""

    # System Level Errors (1000-1099)
    SYSTEM_INITIALIZATION_FAILED = "SYSTEM_1000"
    COMPONENT_INIT_FAILED = "SYSTEM_1001"
    DEPENDENCY_MISSING = "SYSTEM_1002"

    # Device Connection Errors (1100-1199)
    NO_DEVICES_FOUND = "DEVICE_1100"
    DEVICE_NOT_FOUND = "DEVICE_1101"
    DEVICE_OFFLINE = "DEVICE_1102"
    DEVICE_UNAUTHORIZED = "DEVICE_1103"
    DEVICE_CONNECTION_LOST = "DEVICE_1104"
    DEVICE_NOT_RESPONSIVE = "DEVICE_1105"
    ADB_DAEMON_ERROR = "DEVICE_1106"

    # ADB Command Errors (1200-1299)
    ADB_COMMAND_FAILED = "ADB_1200"
    ADB_TIMEOUT = "ADB_1201"
    ADB_PERMISSION_DENIED = "ADB_1202"
    ADB_INVALID_COMMAND = "ADB_1203"
    ADB_EXECUTION_ERROR = "ADB_1204"

    # UI Interaction Errors (1300-1399)
    UI_DUMP_FAILED = "UI_1300"
    ELEMENT_NOT_FOUND = "UI_1301"
    ELEMENT_NOT_CLICKABLE = "UI_1302"
    UI_SERVICE_UNAVAILABLE = "UI_1303"
    COORDINATE_OUT_OF_BOUNDS = "UI_1304"

    # Media Capture Errors (1400-1499)
    SCREENSHOT_FAILED = "MEDIA_1400"
    RECORDING_START_FAILED = "MEDIA_1401"
    RECORDING_STOP_FAILED = "MEDIA_1402"
    MEDIA_PULL_FAILED = "MEDIA_1403"
    STORAGE_INSUFFICIENT = "MEDIA_1404"

    # Input/Interaction Errors (1500-1599)
    TEXT_INPUT_FAILED = "INPUT_1500"
    KEY_EVENT_FAILED = "INPUT_1501"
    TOUCH_EVENT_FAILED = "INPUT_1502"
    GESTURE_FAILED = "INPUT_1503"

    # Log Monitoring Errors (1600-1699)
    LOGCAT_ACCESS_DENIED = "LOG_1600"
    LOG_MONITOR_START_FAILED = "LOG_1601"
    LOG_FILTER_INVALID = "LOG_1602"

    # Validation Errors (1700-1799)
    INVALID_PARAMETER = "VALIDATION_1700"
    MISSING_REQUIRED_PARAM = "VALIDATION_1701"
    PARAMETER_OUT_OF_RANGE = "VALIDATION_1702"

    # Generic Errors (1800-1899)
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    OPERATION_CANCELLED = "GENERIC_1801"
    RESOURCE_UNAVAILABLE = "GENERIC_1802"


@dataclass
class ErrorDetails:
    """Detailed error information structure."""

    code: ErrorCode
    message: str
    context: Dict[str, Any]
    timestamp: datetime
    severity: str  # 'low', 'medium', 'high', 'critical'
    recovery_suggestion: Optional[str] = None
    debug_info: Optional[Dict[str, Any]] = None


class AndroidMCPError(Exception):
    """Base exception class for Android MCP Server errors."""

    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        recovery_suggestions: Optional[List[str]] = None,
    ):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.recovery_suggestions = recovery_suggestions or []
        self.timestamp = datetime.utcnow()
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary representation."""
        return {
            "error_code": self.error_code.value,
            "message": self.message,
            "details": self.details,
            "recovery_suggestions": self.recovery_suggestions,
            "timestamp": self.timestamp.isoformat(),
        }

    def __str__(self) -> str:
        """String representation of the error."""
        return f"[{self.error_code.value}] {self.message}"


class ErrorHandler:
    """Centralized error handling and response formatting."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self._error_history: List[ErrorDetails] = []
        self.error_counts: Dict[ErrorCode, int] = {}
        self.last_errors: Dict[ErrorCode, AndroidMCPError] = {}

    def create_error_response(
        self,
        error: Union[Exception, ErrorCode],
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        recovery_suggestion: Optional[str] = None,
        include_debug: bool = False,
    ) -> Dict[str, Any]:
        """Create standardized error response format."""

        if isinstance(error, AndroidMCPError):
            # Handle custom MCP errors
            error_details = ErrorDetails(
                code=error.error_code,
                message=error.message,
                context=error.details,
                timestamp=error.timestamp,
                severity="medium",
                recovery_suggestion=(
                    error.recovery_suggestions[0]
                    if error.recovery_suggestions
                    else None
                ),
            )
        elif isinstance(error, ErrorCode):
            # Handle direct error code usage
            error_details = ErrorDetails(
                code=error,
                message=message or self._get_default_message(error),
                context=context or {},
                timestamp=datetime.utcnow(),
                severity="medium",
                recovery_suggestion=recovery_suggestion,
            )
        else:
            # Handle generic exceptions
            error_details = ErrorDetails(
                code=ErrorCode.UNKNOWN_ERROR,
                message=message or str(error),
                context=context or {"exception_type": type(error).__name__},
                timestamp=datetime.utcnow(),
                severity="high",
                recovery_suggestion=recovery_suggestion,
            )

        # Add debug information if requested
        if include_debug:
            error_details.debug_info = {
                "traceback": traceback.format_exc(),
                "stack_trace": (
                    traceback.extract_tb(error.__traceback__)
                    if hasattr(error, "__traceback__")
                    else None
                ),
            }

        # Log the error
        self._log_error(error_details)

        # Store in history
        self._error_history.append(error_details)

        # Create response
        response: Dict[str, Any] = {
            "success": False,
            "error": error_details.message,
            "error_code": error_details.code.value,
            "timestamp": error_details.timestamp.isoformat(),
            "severity": error_details.severity,
        }

        if error_details.context:
            response["context"] = error_details.context

        if error_details.recovery_suggestion:
            response["recovery_suggestion"] = error_details.recovery_suggestion

        if error_details.debug_info and include_debug:
            response["debug_info"] = error_details.debug_info

        return response

    def create_success_response(
        self, data: Dict[str, Any], message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create standardized success response format."""
        response: Dict[str, Any] = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if message:
            response["message"] = message

        response.update(data)
        return response

    def wrap_async_operation(self, operation_name: str):
        """Decorator for wrapping async operations with error handling."""

        def decorator(func):
            async def wrapper(*args, **kwargs):
                try:
                    result = await func(*args, **kwargs)
                    if isinstance(result, dict) and "success" in result:
                        return result
                    else:
                        return self.create_success_response(
                            {"result": result},
                            f"{operation_name} completed successfully",
                        )
                except AndroidMCPError as e:
                    return self.create_error_response(e)
                except Exception as e:
                    return self.create_error_response(
                        e,
                        f"{operation_name} failed: {str(e)}",
                        {"operation": operation_name},
                    )

            return wrapper

        return decorator

    def _get_default_message(self, error_code: ErrorCode) -> str:
        """Get default error message for error codes."""
        messages = {
            ErrorCode.NO_DEVICES_FOUND: "No Android devices found. Please connect a device and ensure USB debugging is enabled.",
            ErrorCode.DEVICE_OFFLINE: "Selected device is offline or disconnected.",
            ErrorCode.ADB_TIMEOUT: "ADB command timed out. Device may be unresponsive.",
            ErrorCode.UI_DUMP_FAILED: "Failed to extract UI layout from device.",
            ErrorCode.ELEMENT_NOT_FOUND: "UI element could not be found on screen.",
            ErrorCode.SCREENSHOT_FAILED: "Failed to capture device screenshot.",
            ErrorCode.INVALID_PARAMETER: "One or more parameters are invalid.",
        }
        return messages.get(
            error_code, f"Operation failed with error: {error_code.value}"
        )

    def _log_error(self, error_details: ErrorDetails):
        """Log error with appropriate level and context."""
        log_level_map = {
            "low": logging.INFO,
            "medium": logging.WARNING,
            "high": logging.ERROR,
            "critical": logging.CRITICAL,
        }

        level = log_level_map.get(error_details.severity, logging.ERROR)

        log_message = f"[{error_details.code.value}] {error_details.message}"
        if error_details.context:
            log_message += f" | Context: {error_details.context}"

        self.logger.log(level, log_message)

    def get_error_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent error history."""
        recent_errors = self._error_history[-limit:]
        return [asdict(error) for error in recent_errors]

    def clear_error_history(self):
        """Clear error history."""
        self._error_history.clear()
        self.error_counts.clear()
        self.last_errors.clear()

    def handle_error(
        self, error: AndroidMCPError, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle an AndroidMCPError and return formatted response."""
        # Update error counts
        if error.error_code in self.error_counts:
            self.error_counts[error.error_code] += 1
        else:
            self.error_counts[error.error_code] = 1

        # Store last error of this type
        self.last_errors[error.error_code] = error

        # Create error details for logging and history
        error_details = ErrorDetails(
            code=error.error_code,
            message=error.message,
            context=error.details.copy(),
            timestamp=error.timestamp,
            severity="medium",  # Default severity
            recovery_suggestion=None,
        )

        # Add additional context if provided
        if context:
            error_details.context.update(context)

        # Log the error
        self._log_error(error_details)

        # Store in history
        self._error_history.append(error_details)

        # Get recovery suggestions
        recovery_suggestions = get_recovery_suggestions(
            error.error_code, context=context
        )
        if not recovery_suggestions and error.recovery_suggestions:
            recovery_suggestions = error.recovery_suggestions

        # Create formatted response
        response: Dict[str, Any] = {
            "success": False,
            "error_code": error.error_code.value,
            "message": error.message,
            "timestamp": error.timestamp.isoformat(),
            "recovery_suggestions": recovery_suggestions,
        }

        if error.details:
            response["details"] = error.details

        if context:
            response["context"] = context

        return response

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics."""
        if not self.error_counts:
            return {
                "total_errors": 0,
                "unique_error_types": 0,
                "most_common_error": None,
            }

        total_errors = sum(self.error_counts.values())
        unique_error_types = len(self.error_counts)

        # Find most common error
        most_common_code = max(self.error_counts.items(), key=lambda x: x[1])
        most_common_error = {
            "error_code": most_common_code[0],
            "count": most_common_code[1],
        }

        return {
            "total_errors": total_errors,
            "unique_error_types": unique_error_types,
            "most_common_error": most_common_error,
        }

    def handle_exception(self, exception: Exception, operation: str) -> Dict[str, Any]:
        """Convert a generic exception to AndroidMCPError and handle it."""
        # Determine error code based on exception type
        if isinstance(exception, TimeoutError):
            error_code = ErrorCode.ADB_TIMEOUT
            message = f"Operation '{operation}' timeout: {str(exception)}"
        else:
            error_code = ErrorCode.UNKNOWN_ERROR
            message = f"Operation '{operation}' failed: {str(exception)}"

        # Create AndroidMCPError
        android_error = AndroidMCPError(
            error_code=error_code,
            message=message,
            details={
                "operation": operation,
                "exception_type": type(exception).__name__,
                "exception_message": str(exception),
            },
        )

        # Handle the error
        return self.handle_error(android_error, context={"operation": operation})


# Recovery patterns and suggestions
RECOVERY_SUGGESTIONS = {
    ErrorCode.NO_DEVICES_FOUND: [
        "Connect an Android device via USB",
        "Enable USB debugging in Developer Options",
        "Check ADB drivers installation",
        "Run 'adb devices' to verify connection",
    ],
    ErrorCode.DEVICE_NOT_FOUND: [
        "Check device connection",
        "Verify device ID is correct",
        "Run 'adb devices' to list available devices",
        "Reconnect the device",
    ],
    ErrorCode.DEVICE_OFFLINE: [
        "Reconnect the USB cable",
        "Restart ADB daemon: 'adb kill-server && adb start-server'",
        "Check device authorization dialog",
        "Verify device is unlocked",
    ],
    ErrorCode.DEVICE_CONNECTION_LOST: [
        "Check USB connection stability",
        "Restart ADB daemon",
        "Verify device is not in sleep mode",
        "Reconnect the device",
    ],
    ErrorCode.ADB_COMMAND_FAILED: [
        "Retry the adb command",
        "Check device responsiveness",
        "Verify ADB daemon is running",
        "Restart ADB server if needed",
    ],
    ErrorCode.ADB_TIMEOUT: [
        "Check device responsiveness",
        "Restart the device if frozen",
        "Increase timeout value",
        "Check USB connection stability",
    ],
    ErrorCode.ADB_PERMISSION_DENIED: [
        "Enable root access if required",
        "Check file/directory permissions",
        "Verify ADB is authorized on device",
        "Run command with appropriate permissions",
    ],
    ErrorCode.ADB_DAEMON_ERROR: [
        "Restart ADB daemon",
        "Kill and restart ADB server",
        "Check ADB installation",
        "Verify ADB daemon is running properly",
    ],
    ErrorCode.UI_DUMP_FAILED: [
        "Ensure UIAutomator service is running",
        "Check device screen is unlocked",
        "Verify accessibility permissions",
        "Restart the device if necessary",
    ],
    ErrorCode.ELEMENT_NOT_FOUND: [
        "Wait longer for element to appear",
        "Check UI element selector",
        "Verify app is in expected state",
        "Update element locator strategy",
    ],
    ErrorCode.SCREENSHOT_FAILED: [
        "Check device storage space",
        "Verify screenshot permissions",
        "Ensure device screen is on",
        "Try alternative screenshot method",
    ],
}


def get_recovery_suggestions(
    error_code: ErrorCode, context: Optional[Dict[str, Any]] = None
) -> List[str]:
    """Get recovery suggestions for specific error codes."""
    base_suggestions = RECOVERY_SUGGESTIONS.get(
        error_code,
        [
            "Check device connection and status",
            "Verify ADB is working properly",
            "Restart the operation",
            "Contact support if issue persists",
        ],
    )

    # Add contextual suggestions based on the context
    if context:
        contextual_suggestions = []

        # Add timeout-specific suggestions
        if "timeout" in context:
            contextual_suggestions.append("Increase timeout value")
            contextual_suggestions.append("Check device responsiveness")

        # Add permission-specific suggestions
        if "permission" in str(context).lower():
            contextual_suggestions.append("Check application permissions")
            contextual_suggestions.append(
                "Enable required permissions in device settings"
            )

        # Add storage-specific suggestions
        if "storage" in str(context).lower() or "space" in str(context).lower():
            contextual_suggestions.append("Free up device storage space")
            contextual_suggestions.append("Clear application cache")

        # Combine base and contextual suggestions
        if contextual_suggestions:
            return contextual_suggestions + base_suggestions

    return base_suggestions


def format_error_response(
    error: AndroidMCPError, context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Format an AndroidMCPError into a standardized response."""
    # Get recovery suggestions
    recovery_suggestions = get_recovery_suggestions(error.error_code, context=context)
    if not recovery_suggestions and error.recovery_suggestions:
        recovery_suggestions = error.recovery_suggestions

    # Create response
    response: Dict[str, Any] = {
        "success": False,
        "error_code": error.error_code.value,
        "error": error.message,
        "timestamp": error.timestamp.isoformat(),
        "recovery_suggestions": recovery_suggestions,
    }

    # Add details if present
    if error.details:
        response["details"] = error.details

    # Add context if provided
    if context:
        response["context"] = context

    return response


# Global error handler instance
error_handler = ErrorHandler()
