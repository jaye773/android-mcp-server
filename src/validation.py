"""Input validation and sanitization for Android MCP tools.

This module provides security-focused validation for MCP tool parameters to prevent
command injection vulnerabilities and ensure secure operation of ADB commands.

Non-security validation (ranges, enums, patterns) is handled by Pydantic models
in tool_models.py. This module focuses on:
- Shell metacharacter detection
- Command injection pattern detection
- XSS detection
- Path traversal detection
- Null byte detection
- Input sanitization/escaping
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
            "MEDIA_PLAY",
            "MEDIA_PAUSE",
            "MEDIA_PLAY_PAUSE",
            "MEDIA_STOP",
            "MEDIA_NEXT",
            "MEDIA_PREVIOUS",
            "MEDIA_REWIND",
            "MEDIA_FAST_FORWARD",
            "A", "B", "C", "D", "E", "F", "G", "H", "I", "J",
            "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
            "U", "V", "W", "X", "Y", "Z",
            "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
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


class TextInputValidator:
    """Text input validator class (alias for TextValidator with instance methods)."""

    def __init__(self, security_level: SecurityLevel = SecurityLevel.STRICT):
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


class IdentifierValidator:
    """Validates generic identifier values (monitor IDs, recording IDs, etc.)."""

    # Shell metacharacters that should not appear in identifiers
    SHELL_METACHARACTERS = re.compile(r"[;&|`$(){}><*?!\"'\\]")

    @staticmethod
    def validate_identifier(value: str, field_name: str = "identifier") -> ValidationResult:
        """Validate an identifier is non-empty and contains no shell metacharacters."""
        result = ValidationResult(True)

        if not isinstance(value, str):
            result.add_error(f"{field_name} must be string, got {type(value).__name__}")
            return result

        value = value.strip()
        if not value:
            result.add_error(f"{field_name} cannot be empty")
            return result

        if IdentifierValidator.SHELL_METACHARACTERS.search(value):
            result.add_error(
                f"{field_name} contains invalid characters: shell metacharacters are not allowed"
            )
            return result

        if "\x00" in value:
            result.add_error(f"{field_name} cannot contain null bytes")
            return result

        if len(value) > 500:
            result.add_error(f"{field_name} too long ({len(value)} characters, max 500)")
            return result

        result.sanitized_value = value
        return result


class ComprehensiveValidator:
    """Main validator class coordinating security validation."""

    def __init__(self, security_level: SecurityLevel = SecurityLevel.STRICT):
        self.security_level = security_level

    def validate_key_input(self, keycode: str) -> ValidationResult:
        """Validate key input using TextValidator."""
        return TextValidator.validate_keycode(keycode)

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
        """Validate element search parameters for security (sanitize strings)."""
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

        # Validate each provided parameter for injection safety
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
    "TextValidator",
    "TextInputValidator",
    "KeyInputValidator",
    "PathValidator",
    "FilePathValidator",
    "IdentifierValidator",
    "create_validation_error_response",
    "log_validation_attempt",
]
