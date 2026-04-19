"""Input validation and sanitization for Android MCP tools.

Single-class ``ParameterValidator``; non-security validation lives in
``tool_models.py`` (Pydantic).
"""

import logging
import os
import re
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class SecurityLevel(Enum):
    """Security strictness level used by ParameterValidator."""

    STRICT = "strict"
    MODERATE = "moderate"
    PERMISSIVE = "permissive"

class ValidationResult:
    """Result of a validation operation (valid/sanitized value, errors, warnings)."""

    def __init__(
        self,
        is_valid: bool,
        sanitized_value: Any = None,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
    ):
        """Initialize with validity flag, sanitized value, and optional error/warning lists."""
        self.is_valid = is_valid
        self.sanitized_value = sanitized_value
        self.errors = errors or []
        self.warnings = warnings or []

    def add_error(self, error: str) -> None:
        """Record an error message and mark the result invalid."""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Record a non-fatal warning message."""
        self.warnings.append(warning)

def _fail(msg: str) -> ValidationResult:
    r = ValidationResult(False)
    r.errors.append(msg)
    return r


_SHELL_METACHARS = frozenset(";&|`$()[]{}><*?!\"'\\\n\r\t")
_FILENAME_BAD = {"<", ">", "|", ":", "*", "?", '"', "\x00"}
_INJECTION = [r";\s*\w+", r"&&\s*\w+", r"\|\s*\w+", r"`[^`]*`", r"\$\([^)]*\)",
              r">\s*/", r"<\s*/", r"\\\w+",
              r"<script[^>]*>", r"</script>", r"javascript:", r"on\w+\s*="]
_IDENT_RE = re.compile(r"[;&|`$(){}><*?!\"'\\]")
_DEVICE_RE = re.compile(r"^[A-Za-z0-9._:\-]+$")
_DIRECTIONS = {"up", "down", "left", "right"}
_LOG_PRIORITIES = {"V", "D", "I", "W", "E", "F", "S"}
_KEYCODES = {
    "BACK", "HOME", "MENU", "SEARCH", "VOLUME_UP", "VOLUME_DOWN", "POWER",
    "CAMERA", "FOCUS", "ENTER", "DEL", "TAB", "SPACE", "ESCAPE", "CLEAR",
    "PAGE_UP", "PAGE_DOWN", "MOVE_HOME", "MOVE_END", "INSERT", "FORWARD_DEL",
    "CTRL_LEFT", "CTRL_RIGHT", "CAPS_LOCK", "SCROLL_LOCK", "META_LEFT",
    "META_RIGHT", "FUNCTION", "SYSRQ", "BREAK",
    "MEDIA_PLAY", "MEDIA_PAUSE", "MEDIA_PLAY_PAUSE", "MEDIA_STOP",
    "MEDIA_NEXT", "MEDIA_PREVIOUS", "MEDIA_REWIND", "MEDIA_FAST_FORWARD",
    *"ABCDEFGHIJKLMNOPQRSTUVWXYZ", *"0123456789",
}

class ParameterValidator:
    """Unified security validator for MCP tool parameters."""

    def __init__(self, security_level: SecurityLevel = SecurityLevel.STRICT):
        """Initialize the validator with the given security level."""
        self.security_level = security_level

    @staticmethod
    def _sanitize_shell(text: str, level: SecurityLevel) -> ValidationResult:
        if not isinstance(text, str):
            return _fail(f"Input must be string, got {type(text).__name__}")
        r = ValidationResult(True)
        strict = level == SecurityLevel.STRICT
        report = r.add_error if strict else r.add_warning
        for p in _INJECTION:
            if re.search(p, text, re.IGNORECASE):
                report(f"{'Potentially dangerous' if strict else 'Suspicious'} pattern detected: {p}")
        bad = set(text) & _SHELL_METACHARS
        if bad:
            joined = ", ".join(sorted(bad))
            if strict:
                r.add_error(f"Dangerous shell characters detected: {joined}")
            else:
                for c in bad:
                    text = text.replace(c, f"\\{c}")
                r.add_warning(f"Escaped dangerous characters: {joined}")
        if len(text) > 1000:
            r.add_warning(f"Text input is very long ({len(text)} characters)")
        if "\x00" in text:
            r.add_error("Null bytes not allowed in text input")
            return r
        if strict and len(text) != len(text.strip()):
            r.add_warning("Text contains leading/trailing whitespace")
            text = text.strip()
        r.sanitized_value = text
        if r.errors and strict:
            r.is_valid = False
        return r

    def validate_text(self, text: str, *, max_length: Optional[int] = 1000) -> ValidationResult:
        """Validate and sanitize generic user-supplied text."""
        if not isinstance(text, str):
            return _fail(f"Input must be string, got {type(text).__name__}")
        if max_length is not None and len(text) > max_length:
            return _fail(f"Text length ({len(text)}) exceeds maximum ({max_length})")
        return self._sanitize_shell(text, self.security_level)

    # Back-compat alias (used by src.tools.interaction).
    def validate_text_input(self, text: str) -> ValidationResult:
        """Validate text input intended for `adb shell input text` (back-compat alias)."""
        return self._sanitize_shell(text, self.security_level)

    @staticmethod
    def validate_coordinate(
        x: int, y: int, *, max_x: Optional[int] = None, max_y: Optional[int] = None
    ) -> ValidationResult:
        """Validate an (x, y) screen coordinate pair, optionally bounded by max_x/max_y."""
        for name, v, hi in (("x", x, max_x), ("y", y, max_y)):
            if not isinstance(v, int) or isinstance(v, bool):
                return _fail(f"{name} must be int, got {type(v).__name__}")
            if v < 0:
                return _fail(f"{name} must be non-negative: {v}")
            if hi is not None and v > hi:
                return _fail(f"{name}={v} exceeds max_{name}={hi}")
        return ValidationResult(True, (x, y))

    @staticmethod
    def validate_device_id(device_id: Optional[str]) -> ValidationResult:
        """Validate an ADB device ID (None is allowed and passes through)."""
        if device_id is None:
            return ValidationResult(True, None)
        if not isinstance(device_id, str):
            return _fail(f"device_id must be string, got {type(device_id).__name__}")
        device_id = device_id.strip()
        if not device_id:
            return _fail("device_id cannot be empty")
        if len(device_id) > 100:
            return _fail(f"device_id too long ({len(device_id)} characters, max 100)")
        if not _DEVICE_RE.match(device_id):
            return _fail(f"device_id contains invalid characters: {device_id!r}")
        return ValidationResult(True, device_id)

    @staticmethod
    def validate_filename(filename: str, *, allow_path: bool = False) -> ValidationResult:
        """Validate a filename; rejects path traversal and dangerous characters."""
        if not isinstance(filename, str):
            return _fail(f"Filename must be string, got {type(filename).__name__}")
        if not filename.strip():
            return _fail("Filename cannot be empty")
        filename = filename.strip()
        r = ValidationResult(True)
        if ".." in filename or filename.startswith("/"):
            if not allow_path:
                return _fail(f"Path traversal detected in filename: {filename}")
            r.add_warning(f"Absolute/relative path detected: {filename}")
        bad = set(filename) & _FILENAME_BAD
        if bad:
            return _fail(f"Dangerous characters in filename: {', '.join(sorted(bad))}")
        if len(filename) > 255:
            return _fail(f"Filename too long ({len(filename)} characters)")
        base = os.path.basename(filename).upper()
        if base in {"CON", "PRN", "AUX", "NUL"} or base.startswith(("COM", "LPT")):
            r.add_warning(f"Reserved filename detected: {base}")
        r.sanitized_value = filename
        return r

    @staticmethod
    def validate_identifier(value: str, field_name: str = "identifier") -> ValidationResult:
        """Validate a generic identifier string (resource-id, content-desc, etc.)."""
        if not isinstance(value, str):
            return _fail(f"{field_name} must be string, got {type(value).__name__}")
        value = value.strip()
        if not value:
            return _fail(f"{field_name} cannot be empty")
        if _IDENT_RE.search(value):
            return _fail(f"{field_name} contains invalid characters: shell metacharacters are not allowed")
        if "\x00" in value:
            return _fail(f"{field_name} cannot contain null bytes")
        if len(value) > 500:
            return _fail(f"{field_name} too long ({len(value)} characters, max 500)")
        return ValidationResult(True, value)

    @staticmethod
    def _validate_enum(value: str, allowed: set, field: str, upper: bool) -> ValidationResult:
        if not isinstance(value, str):
            return _fail(f"{field} must be string, got {type(value).__name__}")
        n = value.strip().upper() if upper else value.strip().lower()
        if n not in allowed:
            return _fail(f"Invalid {field} '{value}'. Must be one of: {sorted(allowed)}")
        return ValidationResult(True, n)

    @staticmethod
    def validate_direction(direction: str) -> ValidationResult:
        """Validate a swipe direction (up/down/left/right)."""
        return ParameterValidator._validate_enum(direction, _DIRECTIONS, "direction", upper=False)

    @staticmethod
    def validate_log_priority(priority: str) -> ValidationResult:
        """Validate a logcat priority letter (V/D/I/W/E/F/S)."""
        return ParameterValidator._validate_enum(priority, _LOG_PRIORITIES, "priority", upper=True)

    @staticmethod
    def validate_keycode(keycode: str) -> ValidationResult:
        """Validate an Android keycode (name like KEYCODE_BACK or numeric 0-300)."""
        if not isinstance(keycode, str):
            return _fail(f"Keycode must be string, got {type(keycode).__name__}")
        if keycode.isdigit():
            n = int(keycode)
            if 0 <= n <= 300:
                return ValidationResult(True, str(n))
            return _fail(f"Numeric keycode out of valid range (0-300): {n}")
        upper = keycode.upper()
        if upper in _KEYCODES:
            return ValidationResult(True, upper)
        if upper.startswith("KEYCODE_") and (upper[8:] in _KEYCODES or upper[8:].isdigit()):
            return ValidationResult(True, upper)
        return _fail(f"Unknown Android keycode: {keycode}")

    # Back-compat alias (used by src.tools.interaction).
    def validate_key_input(self, keycode: str) -> ValidationResult:
        """Validate a keycode (back-compat alias for validate_keycode)."""
        return self.validate_keycode(keycode)

    def validate_element_search(
        self, text: Optional[str] = None, resource_id: Optional[str] = None,
        content_desc: Optional[str] = None, class_name: Optional[str] = None,
    ) -> ValidationResult:
        """Validate element-search params; at least one field must be provided."""
        params = {"text": text, "resource_id": resource_id,
                  "content_desc": content_desc, "class_name": class_name}
        if not any(params.values()):
            return _fail("At least one search parameter must be provided")
        r = ValidationResult(True)
        sanitized: Dict[str, str] = {}
        for name, value in params.items():
            if value is None:
                continue
            # UI text stays permissive; IDs/class names use configured level.
            level = SecurityLevel.MODERATE if name in ("text", "content_desc") else self.security_level
            sub = self._sanitize_shell(value, level)
            if sub.is_valid:
                sanitized[name] = sub.sanitized_value
            else:
                r.errors.extend(sub.errors)
                r.warnings.extend(sub.warnings)
        if r.errors:
            r.is_valid = False
        else:
            r.sanitized_value = sanitized
        return r

    @staticmethod
    def validate_bitrate(bitrate: int) -> ValidationResult:
        """Validate a screen-recording bitrate (100kbps to 100Mbps)."""
        if not isinstance(bitrate, int) or isinstance(bitrate, bool):
            return _fail(f"bitrate must be int, got {type(bitrate).__name__}")
        if bitrate < 100_000 or bitrate > 100_000_000:
            return _fail(f"bitrate out of range: {bitrate} (expected 100_000..100_000_000)")
        return ValidationResult(True, bitrate)

    @staticmethod
    def validate_resolution(width: int, height: int) -> ValidationResult:
        """Validate a screen resolution (positive width/height up to 8K)."""
        for name, v, hi in (("width", width, 7680), ("height", height, 4320)):
            if not isinstance(v, int) or isinstance(v, bool):
                return _fail(f"{name} must be int, got {type(v).__name__}")
            if v <= 0 or v > hi:
                return _fail(f"{name} out of range: {v} (expected 1..{hi})")
        return ValidationResult(True, (width, height))

def create_validation_error_response(
    validation_result: ValidationResult, operation: str = "operation"
) -> Dict[str, Any]:
    """Build a standard MCP error response dict from a failed ValidationResult."""
    return {
        "success": False,
        "error": f"Validation failed for {operation}",
        "errors": validation_result.errors,
        "warnings": validation_result.warnings,
        "details": "Input parameters failed security validation",
    }

def log_validation_attempt(
    operation: str, params: Dict[str, Any], result: ValidationResult, logger: logging.Logger
) -> None:
    """Log a validation attempt at the appropriate level based on the result state."""
    if not result.is_valid:
        logger.warning(f"Validation failed for {operation}: {result.errors}. Parameters: {params}")
    elif result.warnings:
        logger.info(f"Validation warnings for {operation}: {result.warnings}. Parameters: {params}")
    else:
        logger.debug(f"Validation passed for {operation}")


# Back-compat alias (legacy name used by some test doubles).
ComprehensiveValidator = ParameterValidator

__all__ = ["ParameterValidator", "ComprehensiveValidator", "SecurityLevel",
           "ValidationResult", "create_validation_error_response", "log_validation_attempt"]
