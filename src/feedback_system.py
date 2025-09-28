"""Enhanced user feedback and error reporting system for Android MCP Server."""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Union, cast
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of operations for progress tracking."""

    DEVICE_DISCOVERY = "device_discovery"
    DEVICE_CONNECTION = "device_connection"
    UI_ANALYSIS = "ui_analysis"
    SCREENSHOT = "screenshot"
    VIDEO_RECORDING = "video_recording"
    LOG_RETRIEVAL = "log_retrieval"
    INPUT_ACTION = "input_action"
    FILE_TRANSFER = "file_transfer"


class MessageSeverity(Enum):
    """Message severity levels."""

    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class OperationProgress:
    """Progress information for long-running operations."""

    operation_id: str
    operation_type: OperationType
    start_time: datetime
    current_step: str
    total_steps: Optional[int] = None
    completed_steps: int = 0
    estimated_duration: Optional[float] = None
    progress_percentage: Optional[float] = None
    details: Optional[str] = None


@dataclass
class EnhancedMessage:
    """Enhanced message with context and suggestions."""

    severity: MessageSeverity
    title: str
    message: str
    operation_context: Optional[str] = None
    error_code: Optional[str] = None
    suggestions: Optional[List[str]] = None
    troubleshooting_tips: Optional[List[str]] = None
    related_docs: Optional[List[str]] = None
    timestamp: Optional[datetime] = None
    operation_duration: Optional[float] = None


class ProgressTracker:
    """Track and report progress for long-running operations."""

    def __init__(self):
        self.active_operations: Dict[str, OperationProgress] = {}
        self.operation_history: List[OperationProgress] = []
        self.progress_callbacks: List[Callable[[OperationProgress], None]] = []

    def start_operation(
        self,
        operation_id: str,
        operation_type: OperationType,
        initial_step: str,
        total_steps: Optional[int] = None,
        estimated_duration: Optional[float] = None,
    ) -> OperationProgress:
        """Start tracking a new operation."""
        progress = OperationProgress(
            operation_id=operation_id,
            operation_type=operation_type,
            start_time=datetime.now(),
            current_step=initial_step,
            total_steps=total_steps,
            estimated_duration=estimated_duration,
        )

        self.active_operations[operation_id] = progress
        self._notify_callbacks(progress)
        return progress

    def update_progress(
        self,
        operation_id: str,
        current_step: str,
        completed_steps: Optional[int] = None,
        details: Optional[str] = None,
    ) -> Optional[OperationProgress]:
        """Update progress for an active operation."""
        if operation_id not in self.active_operations:
            return None

        progress = self.active_operations[operation_id]
        progress.current_step = current_step
        progress.details = details

        if completed_steps is not None:
            progress.completed_steps = completed_steps

            if progress.total_steps:
                progress.progress_percentage = (
                    completed_steps / progress.total_steps
                ) * 100

        self._notify_callbacks(progress)
        return progress

    def complete_operation(self, operation_id: str) -> Optional[OperationProgress]:
        """Mark operation as completed."""
        if operation_id not in self.active_operations:
            return None

        progress = self.active_operations.pop(operation_id)
        progress.current_step = "Completed"
        progress.progress_percentage = 100.0

        self.operation_history.append(progress)
        self._notify_callbacks(progress)
        return progress

    def fail_operation(
        self, operation_id: str, error_details: str
    ) -> Optional[OperationProgress]:
        """Mark operation as failed."""
        if operation_id not in self.active_operations:
            return None

        progress = self.active_operations.pop(operation_id)
        progress.current_step = "Failed"
        progress.details = error_details

        self.operation_history.append(progress)
        self._notify_callbacks(progress)
        return progress

    def get_active_operations(self) -> List[OperationProgress]:
        """Get all currently active operations."""
        return list(self.active_operations.values())

    def add_progress_callback(self, callback: Callable[[OperationProgress], None]):
        """Add a callback for progress updates."""
        self.progress_callbacks.append(callback)

    def _notify_callbacks(self, progress: OperationProgress):
        """Notify all callbacks about progress update."""
        for callback in self.progress_callbacks:
            try:
                callback(progress)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")


class MessageBuilder:
    """Build enhanced messages with context and suggestions."""

    # Common error patterns and solutions
    ERROR_PATTERNS = {
        "no devices": {
            "error_code": "DEVICE_NOT_FOUND",
            "suggestions": [
                "Ensure Android device is connected via USB",
                "Enable USB Debugging in Developer Options",
                "Check USB cable connection",
                "Try running 'adb devices' manually to verify connection",
            ],
            "troubleshooting_tips": [
                "On first connection, accept the USB debugging prompt on device",
                "Some devices require specific USB drivers",
                "Try different USB ports or cables",
                "Restart ADB server: 'adb kill-server && adb start-server'",
            ],
        },
        "device offline": {
            "error_code": "DEVICE_OFFLINE",
            "suggestions": [
                "Disconnect and reconnect the device",
                "Check if device is locked",
                "Restart the device",
                "Re-enable USB debugging",
            ],
        },
        "command timed out": {
            "error_code": "OPERATION_TIMEOUT",
            "suggestions": [
                "Device may be slow or unresponsive",
                "Try increasing the operation timeout",
                "Check device performance and available resources",
                "Restart the device if it appears frozen",
            ],
        },
        "permission denied": {
            "error_code": "PERMISSION_DENIED",
            "suggestions": [
                "Grant necessary permissions on the device",
                "Check if USB debugging is still enabled",
                "Re-accept USB debugging authorization",
                "Try running with different ADB user permissions",
            ],
        },
        "ui dump failed": {
            "error_code": "UI_DUMP_FAILED",
            "suggestions": [
                "Ensure device screen is unlocked",
                "Wait for any animations to complete",
                "Try switching apps or navigating to home screen",
                "Restart the uiautomator service on device",
            ],
        },
        "element not found": {
            "error_code": "ELEMENT_NOT_FOUND",
            "suggestions": [
                "Check if the element text/ID is correct",
                "Wait for page/screen to fully load",
                "Try using partial text matching instead of exact",
                "Verify the element is visible and enabled",
            ],
        },
        "screenshot failed": {
            "error_code": "SCREENSHOT_FAILED",
            "suggestions": [
                "Ensure device screen is on",
                "Check available storage space",
                "Verify device permissions for screenshot",
                "Try waiting a moment and retrying",
            ],
        },
        "recording failed": {
            "error_code": "RECORDING_FAILED",
            "suggestions": [
                "Check device storage space",
                "Ensure no other recordings are active",
                "Try reducing bit rate or resolution",
                "Restart the device if performance is poor",
            ],
        },
    }

    @classmethod
    def create_success_message(
        cls,
        title: str,
        message: str,
        operation_context: Optional[str] = None,
        duration: Optional[float] = None,
    ) -> EnhancedMessage:
        """Create a success message."""
        return EnhancedMessage(
            severity=MessageSeverity.SUCCESS,
            title=title,
            message=message,
            operation_context=operation_context,
            timestamp=datetime.now(),
            operation_duration=duration,
        )

    @classmethod
    def create_error_message(
        cls,
        title: str,
        error: Union[str, Exception],
        operation_context: Optional[str] = None,
        duration: Optional[float] = None,
    ) -> EnhancedMessage:
        """Create an enhanced error message with suggestions."""
        error_str = str(error).lower()

        # Find matching error pattern
        error_code: Optional[str] = None
        suggestions: List[str] = []
        troubleshooting_tips: List[str] = []

        for pattern, info in cls.ERROR_PATTERNS.items():
            if pattern in error_str:
                error_code = cast(Optional[str], info.get("error_code"))
                suggestions = list(info.get("suggestions", []))
                troubleshooting_tips = list(info.get("troubleshooting_tips", []))
                break

        # Generic suggestions if no pattern matched
        if not suggestions:
            suggestions = [
                "Check device connection and status",
                "Retry the operation after a brief wait",
                "Verify device permissions and settings",
            ]

        return EnhancedMessage(
            severity=MessageSeverity.ERROR,
            title=title,
            message=str(error),
            operation_context=operation_context,
            error_code=error_code,
            suggestions=suggestions,
            troubleshooting_tips=troubleshooting_tips,
            timestamp=datetime.now(),
            operation_duration=duration,
        )

    @classmethod
    def create_validation_error(
        cls,
        parameter: str,
        value: Any,
        expected: str,
        operation_context: Optional[str] = None,
    ) -> EnhancedMessage:
        """Create a parameter validation error message."""
        suggestions = [
            f"Expected {parameter} to be {expected}",
            f"Current value: {value} (type: {type(value).__name__})",
            "Check the parameter documentation for valid values",
        ]

        return EnhancedMessage(
            severity=MessageSeverity.ERROR,
            title="Parameter Validation Error",
            message=f"Invalid parameter '{parameter}': {value}",
            operation_context=operation_context,
            error_code="INVALID_PARAMETER",
            suggestions=suggestions,
            timestamp=datetime.now(),
        )

    @classmethod
    def create_warning_message(
        cls,
        title: str,
        message: str,
        operation_context: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
    ) -> EnhancedMessage:
        """Create a warning message."""
        return EnhancedMessage(
            severity=MessageSeverity.WARNING,
            title=title,
            message=message,
            operation_context=operation_context,
            suggestions=suggestions or [],
            timestamp=datetime.now(),
        )


class FeedbackSystem:
    """Main feedback system coordinator."""

    def __init__(self):
        self.progress_tracker = ProgressTracker()
        self.message_builder = MessageBuilder()
        self.feedback_callbacks: List[Callable[[Dict[str, Any]], None]] = []

    def add_feedback_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add a callback for feedback messages."""
        self.feedback_callbacks.append(callback)

    def send_feedback(self, message: EnhancedMessage):
        """Send feedback message to all registered callbacks."""
        feedback_data = {
            "type": "message",
            "severity": message.severity.value,
            "title": message.title,
            "message": message.message,
            "operation_context": message.operation_context,
            "error_code": message.error_code,
            "suggestions": message.suggestions,
            "troubleshooting_tips": message.troubleshooting_tips,
            "timestamp": message.timestamp.isoformat() if message.timestamp else None,
            "operation_duration": message.operation_duration,
        }

        for callback in self.feedback_callbacks:
            try:
                callback(feedback_data)
            except Exception as e:
                logger.warning(f"Feedback callback failed: {e}")

    def send_progress(self, progress: OperationProgress):
        """Send progress update to all registered callbacks."""
        feedback_data = {
            "type": "progress",
            "operation_id": progress.operation_id,
            "operation_type": progress.operation_type.value,
            "current_step": progress.current_step,
            "progress_percentage": progress.progress_percentage,
            "details": progress.details,
            "elapsed_time": (datetime.now() - progress.start_time).total_seconds(),
            "estimated_remaining": self._estimate_remaining_time(progress),
        }

        for callback in self.feedback_callbacks:
            try:
                callback(feedback_data)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")

    def _estimate_remaining_time(self, progress: OperationProgress) -> Optional[float]:
        """Estimate remaining time for operation."""
        if not progress.progress_percentage or progress.progress_percentage <= 0:
            return progress.estimated_duration

        elapsed = (datetime.now() - progress.start_time).total_seconds()
        if progress.progress_percentage >= 100:
            return 0.0

        estimated_total = elapsed * (100 / progress.progress_percentage)
        return max(0, estimated_total - elapsed)

    async def with_progress(
        self,
        operation_type: OperationType,
        operation_name: str,
        operation_func: Callable,
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute operation with progress tracking.

        Args:
            operation_type: Type of operation for progress tracking
            operation_name: Human-readable operation name
            operation_func: Function to execute
            *args, **kwargs: Arguments for the operation function
        """
        operation_id = f"{operation_type.value}_{int(time.time())}"
        start_time = time.time()

        # Start progress tracking
        progress = self.progress_tracker.start_operation(
            operation_id=operation_id,
            operation_type=operation_type,
            initial_step=f"Starting {operation_name}...",
        )
        self.send_progress(progress)

        try:
            # Execute the operation
            if asyncio.iscoroutinefunction(operation_func):
                result = await operation_func(*args, **kwargs)
            else:
                result = operation_func(*args, **kwargs)

            # Complete progress tracking
            duration = time.time() - start_time
            self.progress_tracker.complete_operation(operation_id)

            # Send success feedback
            if isinstance(result, dict) and result.get("success"):
                success_msg = self.message_builder.create_success_message(
                    title=f"{operation_name} Completed",
                    message=f"Operation completed successfully in {duration:.2f} seconds",
                    operation_context=operation_name,
                    duration=duration,
                )
                self.send_feedback(success_msg)

            return result

        except Exception as e:
            # Mark operation as failed
            duration = time.time() - start_time
            self.progress_tracker.fail_operation(operation_id, str(e))

            # Send error feedback
            error_msg = self.message_builder.create_error_message(
                title=f"{operation_name} Failed",
                error=e,
                operation_context=operation_name,
                duration=duration,
            )
            self.send_feedback(error_msg)

            # Return error result
            return {
                "success": False,
                "error": str(e),
                "operation_context": operation_name,
                "duration": duration,
                "feedback": {
                    "error_code": error_msg.error_code,
                    "suggestions": error_msg.suggestions,
                    "troubleshooting_tips": error_msg.troubleshooting_tips,
                },
            }


# Global feedback system instance
feedback_system = FeedbackSystem()


def progress_callback(progress: OperationProgress):
    """Default progress callback that logs to console."""
    if progress.progress_percentage:
        logger.info(
            f"[{progress.operation_type.value}] {progress.current_step} ({progress.progress_percentage:.1f}%)"
        )
    else:
        logger.info(f"[{progress.operation_type.value}] {progress.current_step}")


# Add default progress callback
feedback_system.progress_tracker.add_progress_callback(progress_callback)
