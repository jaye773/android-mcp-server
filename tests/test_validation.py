"""Tests for input validation and sanitization system."""

from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from src.tool_models import (
    DeviceSelectionParams,
    ElementSearchParams,
    SwipeParams,
    TapCoordinatesParams,
)
from src.validation import (
    ParameterValidator,
    SecurityLevel,
    ValidationResult,
    create_validation_error_response,
    log_validation_attempt,
)


class TestValidationResult:
    """Test ValidationResult functionality."""

    def test_validation_result_init(self):
        result = ValidationResult(True, "sanitized", ["error"], ["warning"])

        assert result.is_valid is True
        assert result.sanitized_value == "sanitized"
        assert result.errors == ["error"]
        assert result.warnings == ["warning"]

    def test_add_error(self):
        result = ValidationResult(True)
        result.add_error("Test error")

        assert result.is_valid is False
        assert "Test error" in result.errors

    def test_add_warning(self):
        result = ValidationResult(True)
        result.add_warning("Test warning")

        assert result.is_valid is True
        assert "Test warning" in result.warnings


class TestCoordinateValidationViaPydantic:
    """Test coordinate validation via Pydantic models (unchanged)."""

    def test_valid_coordinates(self):
        params = TapCoordinatesParams(x=100, y=200)
        assert params.x == 100
        assert params.y == 200

    def test_negative_coordinates(self):
        with pytest.raises(ValidationError):
            TapCoordinatesParams(x=-1, y=200)

    def test_out_of_bounds_coordinates(self):
        with pytest.raises(ValidationError):
            TapCoordinatesParams(x=5000, y=200)

    def test_coordinate_boundary_values(self):
        params = TapCoordinatesParams(x=0, y=0)
        assert params.x == 0

        params = TapCoordinatesParams(x=4000, y=4000)
        assert params.x == 4000

    def test_swipe_coordinate_validation(self):
        params = SwipeParams(start_x=100, start_y=200, end_x=300, end_y=400)
        assert params.start_x == 100

        with pytest.raises(ValidationError):
            SwipeParams(start_x=-1, start_y=200, end_x=300, end_y=400)


class TestValidateCoordinate:
    """Test ParameterValidator.validate_coordinate."""

    def test_valid(self):
        result = ParameterValidator.validate_coordinate(10, 20)
        assert result.is_valid
        assert result.sanitized_value == (10, 20)

    def test_negative(self):
        result = ParameterValidator.validate_coordinate(-1, 20)
        assert not result.is_valid

    def test_exceeds_max(self):
        result = ParameterValidator.validate_coordinate(100, 200, max_x=50, max_y=300)
        assert not result.is_valid

    def test_non_int(self):
        result = ParameterValidator.validate_coordinate("10", 20)  # type: ignore[arg-type]
        assert not result.is_valid


class TestDeviceIdValidationViaPydantic:
    """Test device ID validation via Pydantic models."""

    def test_valid_device_id(self):
        valid_ids = ["emulator-5554", "192.168.1.100:5555", "HT7A1A12345", "device123"]

        for device_id in valid_ids:
            params = DeviceSelectionParams(device_id=device_id)
            assert params.device_id == device_id

    def test_invalid_device_id(self):
        invalid_ids = [
            "device;rm -rf /",
            "device`touch /tmp/pwned`",
            "device$(whoami)",
            "device|cat /etc/passwd",
            "device & rm -rf /",
        ]

        for device_id in invalid_ids:
            with pytest.raises(ValidationError):
                DeviceSelectionParams(device_id=device_id)

    def test_empty_device_id_is_none(self):
        params = DeviceSelectionParams()
        assert params.device_id is None

    def test_device_id_max_length(self):
        with pytest.raises(ValidationError):
            DeviceSelectionParams(device_id="a" * 101)


class TestValidateDeviceId:
    """Direct tests for ParameterValidator.validate_device_id."""

    def test_valid(self):
        result = ParameterValidator.validate_device_id("emulator-5554")
        assert result.is_valid
        assert result.sanitized_value == "emulator-5554"

    def test_none(self):
        result = ParameterValidator.validate_device_id(None)
        assert result.is_valid
        assert result.sanitized_value is None

    def test_empty(self):
        result = ParameterValidator.validate_device_id("")
        assert not result.is_valid

    def test_injection(self):
        result = ParameterValidator.validate_device_id("device;rm -rf /")
        assert not result.is_valid

    def test_too_long(self):
        result = ParameterValidator.validate_device_id("a" * 101)
        assert not result.is_valid


class TestValidateText:
    """Test ParameterValidator.validate_text (replaces TextInputValidator)."""

    def test_valid_text_input(self):
        safe_texts = [
            "Hello World",
            "user@example.com",
            "123-456-7890",
            "Test with spaces and numbers 123",
        ]
        v = ParameterValidator(SecurityLevel.MODERATE)
        for text in safe_texts:
            result = v.validate_text(text)
            assert result.is_valid is True, f"Text '{text}' should be valid"

    def test_potentially_dangerous_text_input(self):
        dangerous_texts = [
            "'; DROP TABLE users; --",
            "<script>alert('xss')</script>",
            "$(rm -rf /)",
            "`whoami`",
            "text\nrm -rf /",
        ]

        validator = ParameterValidator(SecurityLevel.STRICT)
        for text in dangerous_texts:
            result = validator.validate_text(text)
            if result.is_valid:
                assert len(result.warnings) > 0, f"Text '{text}' should have warnings"

    def test_text_length_validation(self):
        long_text = "A" * 10000
        v = ParameterValidator(SecurityLevel.MODERATE)
        result = v.validate_text(long_text, max_length=100)
        assert result.is_valid is False
        assert "length" in result.errors[0].lower()

    def test_text_sanitization(self):
        v = ParameterValidator(SecurityLevel.MODERATE)
        result = v.validate_text("  Hello World  ")

        assert result.is_valid is True
        assert result.sanitized_value.strip() == "Hello World"


class TestValidateKeycode:
    """Test ParameterValidator.validate_keycode."""

    def test_valid_key_codes(self):
        valid_keys = [
            "KEYCODE_ENTER",
            "KEYCODE_BACK",
            "KEYCODE_HOME",
            "KEYCODE_MENU",
            "KEYCODE_VOLUME_UP",
            "KEYCODE_A",
            "3",
            "66",
        ]

        for keycode in valid_keys:
            result = ParameterValidator.validate_keycode(keycode)
            assert result.is_valid is True, f"Keycode '{keycode}' should be valid"

    def test_invalid_key_codes(self):
        invalid_keys = [
            "",
            "INVALID_KEY",
            "KEYCODE_; rm -rf /",
            "999999",
            "KEYCODE_`whoami`",
        ]

        for keycode in invalid_keys:
            result = ParameterValidator.validate_keycode(keycode)
            assert result.is_valid is False, f"Keycode '{keycode}' should be invalid"

    def test_numeric_keycode_validation(self):
        result = ParameterValidator.validate_keycode("66")
        assert result.is_valid is True

        result = ParameterValidator.validate_keycode("999")
        assert result.is_valid is False


class TestValidateFilename:
    """Test ParameterValidator.validate_filename (replaces FilePathValidator)."""

    def test_valid_filename(self):
        result = ParameterValidator.validate_filename("screenshot.png")
        assert result.is_valid
        assert result.sanitized_value == "screenshot.png"

    def test_path_traversal(self):
        bad = [
            "../../../etc/passwd",
            "/etc/passwd",
            "screenshots/../../secret",
        ]
        for fn in bad:
            result = ParameterValidator.validate_filename(fn)
            assert not result.is_valid, f"Expected {fn!r} to be invalid"

    def test_dangerous_characters(self):
        result = ParameterValidator.validate_filename("screen?shot.png")
        assert not result.is_valid

    def test_reserved_names_warn(self):
        result = ParameterValidator.validate_filename("CON")
        # Reserved names produce warnings but are still valid
        assert result.is_valid
        assert any("Reserved" in w for w in result.warnings)

    def test_too_long(self):
        result = ParameterValidator.validate_filename("a" * 256)
        assert not result.is_valid

    def test_empty(self):
        result = ParameterValidator.validate_filename("   ")
        assert not result.is_valid


class TestValidateIdentifier:
    """Test ParameterValidator.validate_identifier."""

    def test_valid(self):
        result = ParameterValidator.validate_identifier("monitor_123", "monitor_id")
        assert result.is_valid
        assert result.sanitized_value == "monitor_123"

    def test_shell_metachars_rejected(self):
        result = ParameterValidator.validate_identifier("rec;rm -rf /", "recording_id")
        assert not result.is_valid

    def test_empty(self):
        result = ParameterValidator.validate_identifier("", "monitor_id")
        assert not result.is_valid


class TestValidateDirection:
    """Test ParameterValidator.validate_direction."""

    def test_valid(self):
        for d in ["up", "down", "left", "right", "UP", "Down"]:
            result = ParameterValidator.validate_direction(d)
            assert result.is_valid
            assert result.sanitized_value == d.strip().lower()

    def test_invalid(self):
        for d in ["diagonal", "", "backwards"]:
            result = ParameterValidator.validate_direction(d)
            assert not result.is_valid


class TestValidateLogPriority:
    """Test ParameterValidator.validate_log_priority."""

    def test_valid(self):
        for p in ["V", "D", "I", "W", "E", "F", "S", "e", "i"]:
            result = ParameterValidator.validate_log_priority(p)
            assert result.is_valid
            assert result.sanitized_value == p.strip().upper()

    def test_invalid(self):
        for p in ["Z", "", "XX"]:
            result = ParameterValidator.validate_log_priority(p)
            assert not result.is_valid


class TestValidateBitrate:
    def test_valid(self):
        result = ParameterValidator.validate_bitrate(4_000_000)
        assert result.is_valid

    def test_too_low(self):
        result = ParameterValidator.validate_bitrate(1)
        assert not result.is_valid

    def test_too_high(self):
        result = ParameterValidator.validate_bitrate(10**9)
        assert not result.is_valid


class TestValidateResolution:
    def test_valid(self):
        result = ParameterValidator.validate_resolution(1080, 1920)
        assert result.is_valid
        assert result.sanitized_value == (1080, 1920)

    def test_non_positive(self):
        result = ParameterValidator.validate_resolution(0, 100)
        assert not result.is_valid

    def test_too_large(self):
        result = ParameterValidator.validate_resolution(9000, 9000)
        assert not result.is_valid


class TestElementSearchValidation:
    """Test element search validation via Pydantic and ParameterValidator."""

    def test_valid_element_search_pydantic(self):
        params = ElementSearchParams(
            text="Login Button",
            resource_id="com.app:id/login_btn",
            content_desc="Login button",
            class_name="android.widget.Button",
        )
        assert params.text == "Login Button"

    def test_empty_search_criteria_pydantic(self):
        with pytest.raises(ValidationError):
            ElementSearchParams()

    def test_xss_in_element_search_via_validator(self):
        validator = ParameterValidator(SecurityLevel.STRICT)
        result = validator.validate_element_search(
            text="<script>alert('xss')</script>"
        )
        # With MODERATE level for text params, XSS input is sanitized
        # (shell metacharacters escaped) but still considered valid.
        assert result.is_valid is True
        assert result.sanitized_value is not None
        assert "text" in result.sanitized_value

    def test_element_search_sanitization_via_validator(self):
        validator = ParameterValidator(SecurityLevel.MODERATE)
        result = validator.validate_element_search(
            text="  Login  ", resource_id="  com.app:id/btn  "
        )
        assert result.is_valid is True
        sanitized = result.sanitized_value
        assert sanitized["text"].strip() == "Login"
        assert sanitized["resource_id"].strip() == "com.app:id/btn"


class TestParameterValidator:
    """Test top-level ParameterValidator integration behaviour."""

    def test_validator_initialization(self):
        strict_validator = ParameterValidator(SecurityLevel.STRICT)
        assert strict_validator.security_level == SecurityLevel.STRICT

        moderate_validator = ParameterValidator(SecurityLevel.MODERATE)
        assert moderate_validator.security_level == SecurityLevel.MODERATE

    def test_text_input_validation_integration(self):
        validator = ParameterValidator(SecurityLevel.STRICT)

        result = validator.validate_text_input("Hello World")
        assert result.is_valid is True

        result = validator.validate_text_input("'; DROP TABLE users; --")
        if result.is_valid:
            assert len(result.warnings) > 0

    def test_key_input_validation_integration(self):
        validator = ParameterValidator(SecurityLevel.STRICT)

        result = validator.validate_key_input("KEYCODE_ENTER")
        assert result.is_valid is True

        result = validator.validate_key_input("INVALID_KEY")
        assert result.is_valid is False

    def test_element_search_validation_integration(self):
        validator = ParameterValidator(SecurityLevel.MODERATE)

        result = validator.validate_element_search(
            text="button", resource_id="com.app:id/btn"
        )
        assert result.is_valid is True

        result = validator.validate_element_search()
        assert result.is_valid is False


class TestValidationHelpers:
    """Test validation helper functions."""

    def test_create_validation_error_response(self):
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
        validation_result = ValidationResult(
            False, None, ["Test error"], ["Test warning"]
        )

        mock_logger = Mock()

        log_validation_attempt(
            "test_operation", {"param": "value"}, validation_result, mock_logger
        )

        assert mock_logger.warning.called or mock_logger.error.called


class TestSecurityLevelBehavior:
    """Test different security level behaviors."""

    def test_strict_security_level(self):
        validator = ParameterValidator(SecurityLevel.STRICT)

        result = validator.validate_text_input("<script>alert('test')</script>")
        assert not result.is_valid or len(result.warnings) > 0

    def test_moderate_security_level(self):
        validator = ParameterValidator(SecurityLevel.MODERATE)

        result = validator.validate_text_input("Some <b>bold</b> text")
        assert result.is_valid

    def test_permissive_security_level(self):
        validator = ParameterValidator(SecurityLevel.PERMISSIVE)

        result = validator.validate_text_input("Almost anything goes")
        assert result.is_valid is True

    def test_security_level_edge_cases(self):
        for level in [
            SecurityLevel.STRICT,
            SecurityLevel.MODERATE,
            SecurityLevel.PERMISSIVE,
        ]:
            validator = ParameterValidator(level)

            # Empty and None should not crash.
            validator.validate_text_input("")
            validator.validate_text_input(None)  # type: ignore[arg-type]


class TestValidationPerformance:
    """Test validation performance characteristics."""

    @pytest.mark.performance
    def test_validation_performance(self):
        import time

        validator = ParameterValidator(SecurityLevel.MODERATE)

        start_time = time.time()
        for _ in range(100):
            validator.validate_text_input("test input")
            validator.validate_key_input("KEYCODE_ENTER")
        duration = time.time() - start_time

        assert duration < 1.0, f"Validation took {duration} seconds, should be < 1.0"

    @pytest.mark.performance
    def test_complex_validation_performance(self):
        import time

        validator = ParameterValidator(SecurityLevel.STRICT)
        large_text = "A" * 1000

        start_time = time.time()
        validator.validate_text_input(large_text)
        duration = time.time() - start_time

        assert duration < 0.1, f"Large text validation took {duration} seconds"
