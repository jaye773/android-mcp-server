"""Input validation and sanitization for Android MCP tools.

This module provides comprehensive validation for all MCP tool parameters to prevent
command injection vulnerabilities and ensure secure operation of ADB commands.
"""

import logging
import os
import re
from enum import Enum
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security validation levels."""

    STRICT = "strict"  # Maximum security, reject suspicious patterns
    MODERATE = "moderate"  # Balanced security with usability
    PERMISSIVE = "permissive"  # Minimal validation for development


class ValidationResult:
    """Validation result with detailed feedback."""

    def __init__(
        self,
        is_valid: bool,
        sanitized_value: Any = None,
        errors: List[str] = None,
        warnings: List[str] = None,
    ):
        """Initialize validation result with status and optional details.

        Args:
            is_valid: Whether the validation passed
            sanitized_value: The cleaned/sanitized input value
            errors: List of validation error messages
            warnings: List of validation warning messages
        """
        self.is_valid = is_valid
        self.sanitized_value = sanitized_value
        self.errors = errors or []
        self.warnings = warnings or []

    def add_error(self, error: str):
        """Add validation error."""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str):
        """Add validation warning."""
        self.warnings.append(warning)


class CoordinateValidator:
    """Validates screen coordinates and bounds."""

    @staticmethod
    def validate_coordinate(
        value: int,
        min_val: int = 0,
        max_val: int = 4000,
        field_name: str = "coordinate",
    ) -> ValidationResult:
        """Validate coordinate value."""
        result = ValidationResult(True)

        if not isinstance(value, int):
            result.add_error(
                f"{field_name} must be an integer, got {type(value).__name__}"
            )
            return result

        if value < min_val:
            result.add_error(f"{field_name} cannot be negative: {value}")
            return result

        if value > max_val:
            result.add_error(
                f"{field_name} exceeds maximum bounds ({value} > {max_val})"
            )
            return result

        result.sanitized_value = value
        return result

    @staticmethod
    def validate_coordinate_pair(
        x: int, y: int, screen_width: int = 1440, screen_height: int = 2560
    ) -> ValidationResult:
        """Validate coordinate pair against screen dimensions."""
        result = ValidationResult(True)

        x_result = CoordinateValidator.validate_coordinate(x, field_name="x")
        y_result = CoordinateValidator.validate_coordinate(y, field_name="y")

        result.errors.extend(x_result.errors)
        result.errors.extend(y_result.errors)
        result.warnings.extend(x_result.warnings)
        result.warnings.extend(y_result.warnings)

        if not x_result.is_valid or not y_result.is_valid:
            result.is_valid = False
            return result

        # Check screen bounds with reasonable defaults
        if x > screen_width:
            result.add_warning(
                f"X coordinate {x} exceeds typical screen width {screen_width}"
            )

        if y > screen_height:
            result.add_warning(
                f"Y coordinate {y} exceeds typical screen height {screen_height}"
            )

        result.sanitized_value = {"x": x, "y": y}
        return result

    @staticmethod
    def validate_swipe_coordinates(
        start_x: int, start_y: int, end_x: int, end_y: int
    ) -> ValidationResult:
        """Validate swipe gesture coordinates."""
        result = ValidationResult(True)

        # Validate all coordinates
        coords = [
            (start_x, "start_x"),
            (start_y, "start_y"),
            (end_x, "end_x"),
            (end_y, "end_y"),
        ]

        for coord, name in coords:
            coord_result = CoordinateValidator.validate_coordinate(
                coord, field_name=name
            )
            result.errors.extend(coord_result.errors)
            result.warnings.extend(coord_result.warnings)

        if result.errors:
            result.is_valid = False
            return result

        # Check for valid gesture distance
        distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
        if distance < 10:
            result.add_warning(f"Swipe distance is very small ({distance:.1f} pixels)")
        elif distance > 2000:
            result.add_warning(f"Swipe distance is very large ({distance:.1f} pixels)")

        result.sanitized_value = (start_x, start_y, end_x, end_y)
        return result


class TextValidator:
    """Validates and sanitizes text input for ADB commands."""

    # Dangerous shell characters that need escaping or blocking
    SHELL_METACHARACTERS = set(
        [
            ";",
            "&",
            "|",
            "`",
            "$",
            "(",
            ")",
            "[",
            "]",
            "{",
            "}",
            ">",
            "<",
            "*",
            "?",
            "!",
            '"',
            "'",
            "\\",
            "\n",
            "\r",
            "\t",
        ]
    )

    # Command injection patterns
    INJECTION_PATTERNS = [
        r";\s*\w+",  # Command separator
        r"&&\s*\w+",  # Logical AND
        r"\|\s*\w+",  # Pipe
        r"`[^`]*`",  # Command substitution
        r"\$\([^)]*\)",  # Command substitution
        r">\s*/",  # File redirection
        r"<\s*/",  # File input
        r"\\\w+",  # Backslash escapes
        r"<script[^>]*>",  # Script tags (XSS)
        r"</script>",  # Script end tags
        r"javascript:",  # JavaScript URLs
        r"on\w+\s*=",  # Event handlers
    ]

    @staticmethod
    def sanitize_shell_input(
        text: str, level: SecurityLevel = SecurityLevel.STRICT
    ) -> ValidationResult:
        """Sanitize text input to prevent command injection."""
        result = ValidationResult(True)

        if not isinstance(text, str):
            result.add_error(f"Input must be string, got {type(text).__name__}")
            return result

        original_text = text

        # Check for injection patterns
        for pattern in TextValidator.INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                if level == SecurityLevel.STRICT:
                    result.add_error(
                        f"Potentially dangerous pattern detected: {pattern}"
                    )
                else:
                    result.add_warning(f"Suspicious pattern detected: {pattern}")

        # Check for shell metacharacters
        dangerous_chars = set(text) & TextValidator.SHELL_METACHARACTERS
        if dangerous_chars:
            if level == SecurityLevel.STRICT:
                result.add_error(
                    f"Dangerous shell characters detected: {', '.join(sorted(dangerous_chars))}"
                )
            else:
                # In moderate/permissive mode, escape the characters
                for char in dangerous_chars:
                    text = text.replace(char, f"\\{char}")
                result.add_warning(
                    f"Escaped dangerous characters: {', '.join(sorted(dangerous_chars))}"
                )

        # Length check
        if len(text) > 1000:
            result.add_warning(f"Text input is very long ({len(text)} characters)")

        # Check for null bytes
        if "\x00" in text:
            result.add_error("Null bytes not allowed in text input")
            return result

        # Check for excessive whitespace
        if len(text) != len(text.strip()) and level == SecurityLevel.STRICT:
            result.add_warning("Text contains leading/trailing whitespace")
            text = text.strip()

        result.sanitized_value = text
        if result.errors and level == SecurityLevel.STRICT:
            result.is_valid = False

        logger.debug(
            f"Text validation: '{original_text}' -> '{text}' (valid: {result.is_valid})"
        )
        return result

    @staticmethod
    def validate_keycode(keycode: str) -> ValidationResult:
        """Validate Android keycode input."""
        result = ValidationResult(True)

        if not isinstance(keycode, str):
            result.add_error(f"Keycode must be string, got {type(keycode).__name__}")
            return result

        # Known Android keycodes
        VALID_KEYCODES = {
            "BACK",
            "HOME",
            "MENU",
            "SEARCH",
            "VOLUME_UP",
            "VOLUME_DOWN",
            "POWER",
            "CAMERA",
            "FOCUS",
            "ENTER",
            "DEL",
            "TAB",
            "SPACE",
            "ESCAPE",
            "CLEAR",
            "PAGE_UP",
            "PAGE_DOWN",
            "MOVE_HOME",
            "MOVE_END",
            "INSERT",
            "FORWARD_DEL",
            "CTRL_LEFT",
            "CTRL_RIGHT",
            "CAPS_LOCK",
            "SCROLL_LOCK",
            "META_LEFT",
            "META_RIGHT",
            "FUNCTION",
            "SYSRQ",
            "BREAK",
            "MOVE_HOME",
            "MOVE_END",
            "INSERT",
            "FORWARD_DEL",
            "MEDIA_PLAY",
            "MEDIA_PAUSE",
            "MEDIA_PLAY_PAUSE",
            "MEDIA_STOP",
            "MEDIA_NEXT",
            "MEDIA_PREVIOUS",
            "MEDIA_REWIND",
            "MEDIA_FAST_FORWARD",
            # Add letter keys
            "A",
            "B",
            "C",
            "D",
            "E",
            "F",
            "G",
            "H",
            "I",
            "J",
            "K",
            "L",
            "M",
            "N",
            "O",
            "P",
            "Q",
            "R",
            "S",
            "T",
            "U",
            "V",
            "W",
            "X",
            "Y",
            "Z",
            # Add number keys
            "0",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
        }

        # Also accept numeric keycodes (0-300 range)
        if keycode.isdigit():
            keycode_num = int(keycode)
            if 0 <= keycode_num <= 300:
                result.sanitized_value = str(keycode_num)
                return result
            else:
                result.add_error(
                    f"Numeric keycode out of valid range (0-300): {keycode_num}"
                )
                return result

        # Check against known keycodes
        keycode_upper = keycode.upper()
        if keycode_upper in VALID_KEYCODES:
            result.sanitized_value = keycode_upper
            return result

        # Check for KEYCODE_ prefix
        if keycode_upper.startswith("KEYCODE_"):
            base_code = keycode_upper[8:]
            if base_code in VALID_KEYCODES or base_code.isdigit():
                result.sanitized_value = keycode_upper
                return result

        result.add_error(f"Unknown Android keycode: {keycode}")
        return result


class DeviceIdValidator:
    """Validates Android device IDs and related identifiers."""

    # Valid device ID patterns
    DEVICE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9\-\._:]+$")
    EMULATOR_PATTERN = re.compile(r"^emulator-\d+$")
    SERIAL_PATTERN = re.compile(r"^[a-zA-Z0-9]{8,}$")

    @staticmethod
    def validate_device_id(device_id: str) -> ValidationResult:
        """Validate Android device ID format."""
        result = ValidationResult(True)

        if not isinstance(device_id, str):
            result.add_error(
                f"Device ID must be string, got {type(device_id).__name__}"
            )
            return result

        if not device_id.strip():
            result.add_error("Device ID cannot be empty")
            return result

        device_id = device_id.strip()

        # Length check
        if len(device_id) > 100:
            result.add_error(f"Device ID too long ({len(device_id)} characters)")
            return result

        # Pattern check
        if not DeviceIdValidator.DEVICE_ID_PATTERN.match(device_id):
            result.add_error(f"Invalid device ID format: {device_id}")
            return result

        # Identify device type
        if DeviceIdValidator.EMULATOR_PATTERN.match(device_id):
            result.add_warning("Emulator device detected")
        elif DeviceIdValidator.SERIAL_PATTERN.match(device_id):
            result.add_warning("Physical device detected")
        elif ":" in device_id:
            result.add_warning("Network device detected")

        result.sanitized_value = device_id
        return result


class FilePathValidator:
    """Validates file paths for security."""

    @staticmethod
    def validate_filename(filename: str, allow_path: bool = False) -> ValidationResult:
        """Validate filename for safety."""
        result = ValidationResult(True)

        if not isinstance(filename, str):
            result.add_error(f"Filename must be string, got {type(filename).__name__}")
            return result

        if not filename.strip():
            result.add_error("Filename cannot be empty")
            return result

        filename = filename.strip()

        # Path traversal check
        if ".." in filename or filename.startswith("/"):
            if not allow_path:
                result.add_error(f"Path traversal detected in filename: {filename}")
                return result
            else:
                result.add_warning(f"Absolute/relative path detected: {filename}")

        # Dangerous characters
        dangerous_chars = set(filename) & {"<", ">", "|", ":", "*", "?", '"', "\x00"}
        if dangerous_chars:
            result.add_error(
                f"Dangerous characters in filename: {', '.join(sorted(dangerous_chars))}"
            )
            return result

        # Length check
        if len(filename) > 255:
            result.add_error(f"Filename too long ({len(filename)} characters)")
            return result

        # Reserved names (Windows compatibility)
        base_name = os.path.basename(filename).upper()
        if (
            base_name in {"CON", "PRN", "AUX", "NUL"}
            or base_name.startswith("COM")
            or base_name.startswith("LPT")
        ):
            result.add_warning(f"Reserved filename detected: {base_name}")

        result.sanitized_value = filename
        return result

    @staticmethod
    def validate_android_path(path: str) -> ValidationResult:
        """Validate Android device file paths."""
        result = ValidationResult(True)

        if not isinstance(path, str):
            result.add_error(f"Path must be string, got {type(path).__name__}")
            return result

        if not path.strip():
            result.add_error("Path cannot be empty")
            return result

        path = path.strip()

        # Android path patterns
        valid_prefixes = [
            "/sdcard/",
            "/data/",
            "/system/",
            "/vendor/",
            "/cache/",
            "/tmp/",
        ]
        if not any(path.startswith(prefix) for prefix in valid_prefixes):
            result.add_warning(f"Unusual Android path: {path}")

        # Path traversal check
        if ".." in path:
            result.add_error(f"Path traversal detected: {path}")
            return result

        # Null bytes
        if "\x00" in path:
            result.add_error("Null bytes not allowed in path")
            return result

        result.sanitized_value = path
        return result


class NumericValidator:
    """Validates numeric parameters."""

    @staticmethod
    def validate_duration(
        duration_ms: int, min_duration: int = 50, max_duration: int = 10000
    ) -> ValidationResult:
        """Validate gesture duration in milliseconds."""
        result = ValidationResult(True)

        if not isinstance(duration_ms, int):
            result.add_error(
                f"Duration must be integer, got {type(duration_ms).__name__}"
            )
            return result

        if duration_ms < min_duration:
            result.add_error(
                f"Duration too short: {duration_ms}ms (minimum: {min_duration}ms)"
            )
            return result

        if duration_ms > max_duration:
            result.add_warning(
                f"Duration very long: {duration_ms}ms (maximum recommended: {max_duration}ms)"
            )

        result.sanitized_value = duration_ms
        return result

    @staticmethod
    def validate_distance(
        distance: int, min_distance: int = 1, max_distance: int = 3000
    ) -> ValidationResult:
        """Validate swipe distance in pixels."""
        result = ValidationResult(True)

        if not isinstance(distance, int):
            result.add_error(f"Distance must be integer, got {type(distance).__name__}")
            return result

        if distance < min_distance:
            result.add_error(f"Distance too short: {distance}px")
            return result

        if distance > max_distance:
            result.add_warning(f"Distance very long: {distance}px")

        result.sanitized_value = distance
        return result

    @staticmethod
    def validate_time_limit(time_limit: int, max_limit: int = 600) -> ValidationResult:
        """Validate recording time limit."""
        result = ValidationResult(True)

        if not isinstance(time_limit, int):
            result.add_error(
                f"Time limit must be integer, got {type(time_limit).__name__}"
            )
            return result

        if time_limit <= 0:
            result.add_error(f"Time limit must be positive: {time_limit}")
            return result

        if time_limit > max_limit:
            result.add_warning(
                f"Time limit very long: {time_limit}s (max recommended: {max_limit}s)"
            )

        result.sanitized_value = time_limit
        return result


class DirectionValidator:
    """Validates swipe directions."""

    VALID_DIRECTIONS = {"up", "down", "left", "right"}

    @staticmethod
    def validate_direction(direction: str) -> ValidationResult:
        """Validate swipe direction."""
        result = ValidationResult(True)

        if not isinstance(direction, str):
            result.add_error(
                f"Direction must be string, got {type(direction).__name__}"
            )
            return result

        direction = direction.lower().strip()

        if direction not in DirectionValidator.VALID_DIRECTIONS:
            result.add_error(
                f"Invalid direction: {direction}. Valid: {', '.join(DirectionValidator.VALID_DIRECTIONS)}"
            )
            return result

        result.sanitized_value = direction
        return result


class LogPriorityValidator:
    """Validates Android log priorities."""

    VALID_PRIORITIES = {
        "V",
        "D",
        "I",
        "W",
        "E",
        "F",
        "S",
    }  # Verbose, Debug, Info, Warning, Error, Fatal, Silent

    @staticmethod
    def validate_priority(priority: str) -> ValidationResult:
        """Validate log priority level."""
        result = ValidationResult(True)

        if not isinstance(priority, str):
            result.add_error(f"Priority must be string, got {type(priority).__name__}")
            return result

        priority = priority.upper().strip()

        if priority not in LogPriorityValidator.VALID_PRIORITIES:
            result.add_error(
                f"Invalid log priority: {priority}. Valid: {', '.join(LogPriorityValidator.VALID_PRIORITIES)}"
            )
            return result

        result.sanitized_value = priority
        return result


class TextInputValidator:
    """Text input validator class (alias for TextValidator with instance methods)."""

    def __init__(self, security_level: SecurityLevel = SecurityLevel.STRICT):
        """Initialize text input validator with security level.

        Args:
            security_level: Security validation level to apply
        """
        self.security_level = security_level

    @staticmethod
    def validate_text_input(text: str, max_length: int = None) -> ValidationResult:
        """Validate text input for safety."""
        if max_length is not None and len(text) > max_length:
            result = ValidationResult(False)
            result.add_error(
                f"Text length ({len(text)}) exceeds maximum ({max_length})"
            )
            return result

        return TextValidator.sanitize_shell_input(text, SecurityLevel.MODERATE)

    def validate_text_input_instance(self, text: str) -> ValidationResult:
        """Instance method for text validation."""
        return TextValidator.sanitize_shell_input(text, self.security_level)


class KeyInputValidator:
    """Key input validator for Android keycodes."""

    @staticmethod
    def validate_key_input(keycode: str) -> ValidationResult:
        """Validate Android keycode input."""
        return TextValidator.validate_keycode(keycode)


class PathValidator:
    """Path validator for file system paths."""

    @staticmethod
    def validate_path(path: str, android_safe: bool = False) -> ValidationResult:
        """Validate file system path for security."""
        result = ValidationResult(True)

        if not isinstance(path, str):
            result.add_error(f"Path must be string, got {type(path).__name__}")
            return result

        if not path.strip():
            result.add_error("Path cannot be empty")
            return result

        path = path.strip()

        # Path traversal check
        if ".." in path:
            result.add_error(f"Path traversal detected: {path}")
            return result

        # Null bytes check
        if "\x00" in path:
            result.add_error("Null bytes not allowed in path")
            return result

        # Windows path check on Unix-like systems (suspicious)
        if "\\" in path and ("C:" in path or "windows" in path.lower()):
            result.add_error(f"Suspicious Windows path detected: {path}")
            return result

        # URL-like paths
        if path.startswith(("file://", "http://", "https://", "ftp://")):
            result.add_error(f"URL-like path not allowed: {path}")
            return result

        # Android-specific validation
        if android_safe:
            android_prefixes = [
                "/sdcard/",
                "/data/local/tmp/",
                "/storage/emulated/",
                "/data/local/",
                "/cache/",
                "/tmp/",
            ]
            if (
                not any(path.startswith(prefix) for prefix in android_prefixes)
                and not path.startswith("./")
                and "/" in path
            ):
                result.add_error(f"Path not in Android-safe location: {path}")
                return result

        result.sanitized_value = path
        return result


class ElementSearchValidator:
    """Element search parameter validator."""

    @staticmethod
    def validate_element_search(
        text: str = None,
        resource_id: str = None,
        content_desc: str = None,
        class_name: str = None,
        security_level: SecurityLevel = SecurityLevel.MODERATE,
    ) -> ValidationResult:
        """Validate element search parameters."""
        result = ValidationResult(True)

        search_params = {
            "text": text,
            "resource_id": resource_id,
            "content_desc": content_desc,
            "class_name": class_name,
        }

        # At least one search parameter must be provided
        provided_params = {k: v for k, v in search_params.items() if v is not None}
        if not provided_params:
            result.add_error("At least one search criteria must be provided")
            return result

        sanitized_params = {}

        # Validate each provided parameter
        for param_name, param_value in provided_params.items():
            if param_name in ["text", "content_desc"]:
                # Use provided security level for text parameters too
                text_result = TextValidator.sanitize_shell_input(
                    param_value, security_level
                )
            else:
                # Stricter validation for IDs and class names
                text_result = TextValidator.sanitize_shell_input(
                    param_value, security_level
                )

            if text_result.is_valid:
                sanitized_params[param_name] = text_result.sanitized_value
            else:
                result.errors.extend(text_result.errors)
                result.warnings.extend(text_result.warnings)

        if result.errors:
            result.is_valid = False
        else:
            result.sanitized_value = sanitized_params

        return result


class ComprehensiveValidator:
    """Main validator class coordinating all validation types."""

    def __init__(self, security_level: SecurityLevel = SecurityLevel.STRICT):
        """Initialize comprehensive validator with security level.

        Args:
            security_level: Security validation level for all operations
        """
        self.security_level = security_level

    def validate_tap_coordinates(
        self, x: int, y: int, screen_width: int = None, screen_height: int = None
    ) -> ValidationResult:
        """Validate tap coordinates."""
        return CoordinateValidator.validate_coordinate_pair(
            x, y, screen_width or 1440, screen_height or 2560
        )

    def validate_coordinates(
        self, x: int, y: int, screen_width: int = None, screen_height: int = None
    ) -> ValidationResult:
        """Validate coordinates (alias for validate_tap_coordinates)."""
        return self.validate_tap_coordinates(x, y, screen_width, screen_height)

    def validate_key_input(self, keycode: str) -> ValidationResult:
        """Validate key input using TextValidator."""
        return TextValidator.validate_keycode(keycode)

    def validate_swipe_gesture(
        self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300
    ) -> ValidationResult:
        """Validate complete swipe gesture parameters."""
        result = ValidationResult(True)

        # Validate coordinates
        coord_result = CoordinateValidator.validate_swipe_coordinates(
            start_x, start_y, end_x, end_y
        )
        result.errors.extend(coord_result.errors)
        result.warnings.extend(coord_result.warnings)

        # Validate duration
        duration_result = NumericValidator.validate_duration(duration_ms)
        result.errors.extend(duration_result.errors)
        result.warnings.extend(duration_result.warnings)

        if result.errors:
            result.is_valid = False
        else:
            result.sanitized_value = {
                "start_x": start_x,
                "start_y": start_y,
                "end_x": end_x,
                "end_y": end_y,
                "duration_ms": duration_ms,
            }

        return result

    def validate_text_input(self, text: str) -> ValidationResult:
        """Validate text input for ADB commands."""
        return TextValidator.sanitize_shell_input(text, self.security_level)

    def validate_element_search(
        self,
        text: str = None,
        resource_id: str = None,
        content_desc: str = None,
        class_name: str = None,
    ) -> ValidationResult:
        """Validate element search parameters."""
        result = ValidationResult(True)

        search_params = {
            "text": text,
            "resource_id": resource_id,
            "content_desc": content_desc,
            "class_name": class_name,
        }

        # At least one search parameter must be provided
        if not any(param for param in search_params.values()):
            result.add_error("At least one search parameter must be provided")
            return result

        sanitized_params = {}

        # Validate each provided parameter
        for param_name, param_value in search_params.items():
            if param_value is not None:
                if param_name in ["text", "content_desc"]:
                    # More permissive validation for UI text
                    text_result = TextValidator.sanitize_shell_input(
                        param_value, SecurityLevel.MODERATE
                    )
                else:
                    # Stricter validation for IDs and class names
                    text_result = TextValidator.sanitize_shell_input(
                        param_value, self.security_level
                    )

                if text_result.is_valid:
                    sanitized_params[param_name] = text_result.sanitized_value
                else:
                    result.errors.extend(text_result.errors)
                    result.warnings.extend(text_result.warnings)

        if result.errors:
            result.is_valid = False
        else:
            result.sanitized_value = sanitized_params

        return result


def create_validation_error_response(
    validation_result: ValidationResult, operation: str = "operation"
) -> Dict[str, Any]:
    """Create standardized error response for validation failures."""
    return {
        "success": False,
        "error": f"Validation failed for {operation}",
        "errors": validation_result.errors,
        "warnings": validation_result.warnings,
        "details": "Input parameters failed security validation",
    }


def log_validation_attempt(
    operation: str,
    params: Dict[str, Any],
    result: ValidationResult,
    logger: logging.Logger,
):
    """Log validation attempts for security monitoring."""
    if not result.is_valid:
        logger.warning(
            f"Validation failed for {operation}: {result.errors}. "
            f"Parameters: {params}"
        )
    elif result.warnings:
        logger.info(
            f"Validation warnings for {operation}: {result.warnings}. "
            f"Parameters: {params}"
        )
    else:
        logger.debug(f"Validation passed for {operation}")


# Export main classes and functions
__all__ = [
    "ValidationResult",
    "SecurityLevel",
    "ComprehensiveValidator",
    "CoordinateValidator",
    "TextValidator",
    "TextInputValidator",
    "KeyInputValidator",
    "PathValidator",
    "ElementSearchValidator",
    "DeviceIdValidator",
    "FilePathValidator",
    "NumericValidator",
    "DirectionValidator",
    "LogPriorityValidator",
    "create_validation_error_response",
    "log_validation_attempt",
]
