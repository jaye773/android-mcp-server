import pytest
from pydantic import ValidationError

from src.tool_models import (
    LogcatParams,
    SwipeDirectionParams,
    TapCoordinatesParams,
)
from src.validation import ParameterValidator, SecurityLevel


def test_direction_via_pydantic():
    params = SwipeDirectionParams(direction="up")
    assert params.direction == "up"

    # Case-insensitive via field_validator
    params = SwipeDirectionParams(direction="UP")
    assert params.direction == "up"

    with pytest.raises(ValidationError):
        SwipeDirectionParams(direction="diagonal")


def test_log_priority_via_pydantic():
    params = LogcatParams(priority="e")
    assert params.priority == "E"

    params = LogcatParams(priority="I")
    assert params.priority == "I"

    with pytest.raises(ValidationError):
        LogcatParams(priority="Z")


def test_filename_traversal():
    ok = ParameterValidator.validate_filename("file.txt")
    assert ok.is_valid
    bad = ParameterValidator.validate_filename("../../etc/passwd")
    assert not bad.is_valid


def test_text_sanitize_moderate():
    v = ParameterValidator(SecurityLevel.MODERATE)
    res = v.validate_text("hello; rm -rf /")
    # MODERATE should sanitize (escape) rather than error out.
    assert res is not None


def test_coordinate_via_pydantic():
    params = TapCoordinatesParams(x=10, y=20)
    assert params.x == 10 and params.y == 20

    with pytest.raises(ValidationError):
        TapCoordinatesParams(x=-1, y=20)

    with pytest.raises(ValidationError):
        TapCoordinatesParams(x=10, y=5000)


def test_duration_via_pydantic():
    from src.tool_models import SwipeParams

    params = SwipeParams(start_x=0, start_y=0, end_x=5, end_y=5, duration_ms=300)
    assert params.duration_ms == 300

    with pytest.raises(ValidationError):
        SwipeParams(start_x=0, start_y=0, end_x=5, end_y=5, duration_ms=10)


def test_distance_via_pydantic():
    params = SwipeDirectionParams(direction="up", distance=100)
    assert params.distance == 100

    with pytest.raises(ValidationError):
        SwipeDirectionParams(direction="up", distance=0)

    with pytest.raises(ValidationError):
        SwipeDirectionParams(direction="up", distance=5000)
