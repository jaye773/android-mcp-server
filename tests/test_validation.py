"""Tests for input validation and sanitization system."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from src.tool_models import (
    DeviceSelectionParams,
    ElementSearchParams,
    LogcatParams,
    RecordingParams,
    SwipeDirectionParams,
    SwipeParams,
    TapCoordinatesParams,
    TapElementParams,
)
from src.validation import (
    ComprehensiveValidator,
    FilePathValidator,
    KeyInputValidator,
    PathValidator,
    SecurityLevel,
    TextInputValidator,
    TextValidator,
    ValidationResult,
    create_validation_error_response,
    log_validation_attempt,
)


class TestValidationResult:
    """Test ValidationResult functionality."""

    def test_validation_result_init(self):
        """Test ValidationResult initialization."""
        result = ValidationResult(True, "sanitized", ["error"], ["warning"])

        assert result.is_valid is True
        assert result.sanitized_value == "sanitized"
        assert result.errors == ["error"]
        assert result.warnings == ["warning"]

    def test_add_error(self):
        """Test adding validation errors."""
        result = ValidationResult(True)
        result.add_error("Test error")

        assert result.is_valid is False
        assert "Test error" in result.errors

    def test_add_warning(self):
        """Test adding validation warnings."""
        result = ValidationResult(True)
        result.add_warning("Test warning")

        assert result.is_valid is True
        assert "Test warning" in result.warnings


class TestCoordinateValidationViaPydantic:
    """Test coordinate validation via Pydantic models."""

    def test_valid_coordinates(self):
        """Test validation of valid coordinates."""
        params = TapCoordinatesParams(x=100, y=200)
        assert params.x == 100
        assert params.y == 200

    def test_negative_coordinates(self):
        """Test validation of negative coordinates."""
        with pytest.raises(ValidationError):
            TapCoordinatesParams(x=-1, y=200)

    def test_out_of_bounds_coordinates(self):
        """Test validation of out-of-bounds coordinates."""
        with pytest.raises(ValidationError):
            TapCoordinatesParams(x=5000, y=200)

    def test_coordinate_boundary_values(self):
        """Test coordinate boundary values."""
        # Min valid
        params = TapCoordinatesParams(x=0, y=0)
        assert params.x == 0

        # Max valid
        params = TapCoordinatesParams(x=4000, y=4000)
        assert params.x == 4000

    def test_swipe_coordinate_validation(self):
        """Test swipe coordinate validation via Pydantic."""
        params = SwipeParams(start_x=100, start_y=200, end_x=300, end_y=400)
        assert params.start_x == 100

        with pytest.raises(ValidationError):
            SwipeParams(start_x=-1, start_y=200, end_x=300, end_y=400)


class TestDeviceIdValidationViaPydantic:
    """Test device ID validation via Pydantic models."""

    def test_valid_device_id(self):
        """Test validation of valid device IDs."""
        valid_ids = ["emulator-5554", "192.168.1.100:5555", "HT7A1A12345", "device123"]

        for device_id in valid_ids:
            params = DeviceSelectionParams(device_id=device_id)
            assert params.device_id == device_id

    def test_invalid_device_id(self):
        """Test validation of invalid device IDs."""
        invalid_ids = [
            "device;rm -rf /",  # Command injection
            "device`touch /tmp/pwned`",  # Command injection
            "device$(whoami)",  # Command substitution
            "device|cat /etc/passwd",  # Pipe injection
            "device & rm -rf /",  # Background command
        ]

        for device_id in invalid_ids:
            with pytest.raises(ValidationError):
                DeviceSelectionParams(device_id=device_id)

    def test_empty_device_id_is_none(self):
        """Test that omitting device_id defaults to None."""
        params = DeviceSelectionParams()
        assert params.device_id is None

    def test_device_id_max_length(self):
        """Test device ID max length constraint."""
        with pytest.raises(ValidationError):
            DeviceSelectionParams(device_id="a" * 101)


class TestTextInputValidator:
    """Test text input validation."""

    def test_valid_text_input(self):
        """Test validation of safe text input."""
        safe_texts = [
            "Hello World",
            "user@example.com",
            "123-456-7890",
            "Test with spaces and numbers 123",
        ]

        for text in safe_texts:
            result = TextInputValidator.validate_text_input(text)
            assert result.is_valid is True, f"Text '{text}' should be valid"

    def test_potentially_dangerous_text_input(self):
        """Test validation of potentially dangerous text input."""
        dangerous_texts = [
            "'; DROP TABLE users; --",  # SQL injection
            "<script>alert('xss')</script>",  # XSS
            "$(rm -rf /)",  # Command substitution
            "`whoami`",  # Command execution
            "text\nrm -rf /",  # Newline injection
        ]

        validator = TextInputValidator(SecurityLevel.STRICT)

        for text in dangerous_texts:
            result = validator.validate_text_input(text)
            if result.is_valid:
                # Should at least have warnings
                assert len(result.warnings) > 0, f"Text '{text}' should have warnings"

    def test_text_length_validation(self):
        """Test text length validation."""
        # Very long text
        long_text = "A" * 10000

        result = TextInputValidator.validate_text_input(long_text, max_length=100)
        assert result.is_valid is False
        assert "length" in result.errors[0].lower()

    def test_text_sanitization(self):
        """Test text sanitization."""
        result = TextInputValidator.validate_text_input("  Hello World  ")

        assert result.is_valid is True
        # Should preserve meaningful whitespace but trim edges
        assert result.sanitized_value.strip() == "Hello World"


class TestKeyInputValidator:
    """Test key input validation."""

    def test_valid_key_codes(self):
        """Test validation of valid Android key codes."""
        valid_keys = [
            "KEYCODE_ENTER",
            "KEYCODE_BACK",
            "KEYCODE_HOME",
            "KEYCODE_MENU",
            "KEYCODE_VOLUME_UP",
            "KEYCODE_A",
            "3",  # Numeric keycode
            "66",  # ENTER keycode
        ]

        for keycode in valid_keys:
            result = KeyInputValidator.validate_key_input(keycode)
            assert result.is_valid is True, f"Keycode '{keycode}' should be valid"

    def test_invalid_key_codes(self):
        """Test validation of invalid key codes."""
        invalid_keys = [
            "",  # Empty
            "INVALID_KEY",
            "KEYCODE_; rm -rf /",  # Command injection
            "999999",  # Invalid numeric keycode
            "KEYCODE_`whoami`",  # Command execution
        ]

        for keycode in invalid_keys:
            result = KeyInputValidator.validate_key_input(keycode)
            assert result.is_valid is False, f"Keycode '{keycode}' should be invalid"

    def test_numeric_keycode_validation(self):
        """Test validation of numeric keycodes."""
        # Valid range
        result = KeyInputValidator.validate_key_input("66")  # ENTER
        assert result.is_valid is True

        # Invalid range
        result = KeyInputValidator.validate_key_input("999")
        assert result.is_valid is False


class TestPathValidator:
    """Test path validation."""

    def test_valid_paths(self):
        """Test validation of safe file paths."""
        valid_paths = [
            "/sdcard/screenshot.png",
            "/data/local/tmp/test.txt",
            "screenshot.png",
            "./test.log",
        ]

        for path in valid_paths:
            result = PathValidator.validate_path(path)
            assert result.is_valid is True, f"Path '{path}' should be valid"

    def test_path_traversal_attempts(self):
        """Test detection of path traversal attempts."""
        dangerous_paths = [
            "../../../etc/passwd",
            "/data/../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "/sdcard/../../../root/.ssh/id_rsa",
            "file:///etc/passwd",
            "C:\\windows\\system32\\config\\sam",
        ]

        for path in dangerous_paths:
            result = PathValidator.validate_path(path)
            assert result.is_valid is False, f"Path '{path}' should be invalid"

    def test_path_sanitization(self):
        """Test path sanitization."""
        result = PathValidator.validate_path("  /sdcard/test.png  ")

        assert result.is_valid is True
        assert result.sanitized_value == "/sdcard/test.png"

    def test_android_specific_path_validation(self):
        """Test Android-specific path validation."""
        # Android-safe paths
        android_paths = [
            "/sdcard/DCIM/camera/IMG_001.jpg",
            "/data/local/tmp/test.db",
            "/storage/emulated/0/Download/file.pdf",
        ]

        for path in android_paths:
            result = PathValidator.validate_path(path, android_safe=True)
            assert result.is_valid is True

        # Non-Android paths
        non_android_path = "/etc/passwd"
        result = PathValidator.validate_path(non_android_path, android_safe=True)
        assert result.is_valid is False


class TestElementSearchValidation:
    """Test element search validation via Pydantic and ComprehensiveValidator."""

    def test_valid_element_search_pydantic(self):
        """Test Pydantic model_validator for element search."""
        params = ElementSearchParams(
            text="Login Button",
            resource_id="com.app:id/login_btn",
            content_desc="Login button",
            class_name="android.widget.Button",
        )
        assert params.text == "Login Button"

    def test_empty_search_criteria_pydantic(self):
        """Test that empty search criteria raises ValidationError."""
        with pytest.raises(ValidationError):
            ElementSearchParams()

    def test_xss_in_element_search_via_validator(self):
        """Test detection of XSS attempts via ComprehensiveValidator."""
        validator = ComprehensiveValidator(SecurityLevel.STRICT)
        result = validator.validate_element_search(
            text="<script>alert('xss')</script>"
        )
        # Should be invalid or have warnings
        if result.is_valid:
            assert len(result.warnings) > 0

    def test_element_search_sanitization_via_validator(self):
        """Test sanitization of element search parameters via ComprehensiveValidator."""
        validator = ComprehensiveValidator(SecurityLevel.MODERATE)
        result = validator.validate_element_search(
            text="  Login  ", resource_id="  com.app:id/btn  "
        )
        assert result.is_valid is True
        sanitized = result.sanitized_value
        assert sanitized["text"].strip() == "Login"
        assert sanitized["resource_id"].strip() == "com.app:id/btn"


class TestComprehensiveValidator:
    """Test comprehensive validation system."""

    def test_validator_initialization(self):
        """Test validator initialization with different security levels."""
        # Strict validator
        strict_validator = ComprehensiveValidator(SecurityLevel.STRICT)
        assert strict_validator.security_level == SecurityLevel.STRICT

        # Moderate validator
        moderate_validator = ComprehensiveValidator(SecurityLevel.MODERATE)
        assert moderate_validator.security_level == SecurityLevel.MODERATE

    def test_text_input_validation_integration(self):
        """Test text input validation through comprehensive validator."""
        validator = ComprehensiveValidator(SecurityLevel.STRICT)

        result = validator.validate_text_input("Hello World")
        assert result.is_valid is True

        # Test with potentially dangerous input
        result = validator.validate_text_input("'; DROP TABLE users; --")
        if result.is_valid:
            assert len(result.warnings) > 0

    def test_key_input_validation_integration(self):
        """Test key input validation through comprehensive validator."""
        validator = ComprehensiveValidator(SecurityLevel.STRICT)

        result = validator.validate_key_input("KEYCODE_ENTER")
        assert result.is_valid is True

        result = validator.validate_key_input("INVALID_KEY")
        assert result.is_valid is False

    def test_element_search_validation_integration(self):
        """Test element search validation through comprehensive validator."""
        validator = ComprehensiveValidator(SecurityLevel.MODERATE)

        result = validator.validate_element_search(
            text="button", resource_id="com.app:id/btn"
        )
        assert result.is_valid is True

        result = validator.validate_element_search()  # No criteria
        assert result.is_valid is False


class TestValidationHelpers:
    """Test validation helper functions."""

    def test_create_validation_error_response(self):
        """Test validation error response creation."""
        validation_result = ValidationResult(
            False, None, ["Invalid input", "Security violation"], ["Minor issue"]
        )

        response = create_validation_error_response(validation_result, "test operation")

        assert response["success"] is False
        assert "error" in response
        assert "validation" in response["error"].lower()
        assert "errors" in response
        assert len(response["errors"]) == 2

    def test_log_validation_attempt(self):
        """Test validation attempt logging."""
        validation_result = ValidationResult(
            False, None, ["Test error"], ["Test warning"]
        )

        mock_logger = Mock()

        log_validation_attempt(
            "test_operation", {"param": "value"}, validation_result, mock_logger
        )

        # Should have logged the validation attempt
        assert mock_logger.warning.called or mock_logger.error.called


class TestSecurityLevelBehavior:
    """Test different security level behaviors."""

    def test_strict_security_level(self):
        """Test strict security level behavior."""
        validator = ComprehensiveValidator(SecurityLevel.STRICT)

        # Should reject potentially dangerous input
        result = validator.validate_text_input("<script>alert('test')</script>")
        # Either invalid or has warnings
        assert not result.is_valid or len(result.warnings) > 0

    def test_moderate_security_level(self):
        """Test moderate security level behavior."""
        validator = ComprehensiveValidator(SecurityLevel.MODERATE)

        # Should be more permissive but still cautious
        result = validator.validate_text_input("Some <b>bold</b> text")
        # Should be valid but might have warnings
        assert result.is_valid

    def test_permissive_security_level(self):
        """Test permissive security level behavior."""
        validator = ComprehensiveValidator(SecurityLevel.PERMISSIVE)

        # Should allow most input for development
        result = validator.validate_text_input("Almost anything goes")
        assert result.is_valid is True

    def test_security_level_edge_cases(self):
        """Test security level handling of edge cases."""
        for level in [
            SecurityLevel.STRICT,
            SecurityLevel.MODERATE,
            SecurityLevel.PERMISSIVE,
        ]:
            validator = ComprehensiveValidator(level)

            # Empty input should be handled consistently
            result = validator.validate_text_input("")
            # Behavior may vary by level, but should not crash

            # Null input should be handled
            result = validator.validate_text_input(None)
            # Should handle gracefully


class TestValidationPerformance:
    """Test validation performance characteristics."""

    @pytest.mark.performance
    def test_validation_performance(self):
        """Test that validation operations complete quickly."""
        import time

        validator = ComprehensiveValidator(SecurityLevel.MODERATE)

        start_time = time.time()

        # Run multiple validations
        for _ in range(100):
            validator.validate_text_input("test input")
            validator.validate_key_input("KEYCODE_ENTER")

        end_time = time.time()
        duration = end_time - start_time

        # Should complete 300 validations in reasonable time
        assert duration < 1.0, f"Validation took {duration} seconds, should be < 1.0"

    @pytest.mark.performance
    def test_complex_validation_performance(self):
        """Test performance of complex validation scenarios."""
        import time

        validator = ComprehensiveValidator(SecurityLevel.STRICT)

        # Large text input
        large_text = "A" * 1000

        start_time = time.time()
        result = validator.validate_text_input(large_text)
        end_time = time.time()

        duration = end_time - start_time
        assert duration < 0.1, f"Large text validation took {duration} seconds"
