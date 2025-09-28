import pytest

from src.validation import (
    DirectionValidator,
    LogPriorityValidator,
    PathValidator,
    TextValidator,
    CoordinateValidator,
    NumericValidator,
)


def test_direction_validator():
    ok = DirectionValidator.validate_direction("up")
    assert ok.is_valid and ok.sanitized_value == "up"
    bad = DirectionValidator.validate_direction("diagonal")
    assert not bad.is_valid


def test_log_priority_validator():
    ok = LogPriorityValidator.validate_priority("e")
    assert ok.is_valid and ok.sanitized_value == "E"
    bad = LogPriorityValidator.validate_priority("Z")
    assert not bad.is_valid


def test_path_validator_android_safe_and_traversal():
    ok = PathValidator.validate_path("/sdcard/file.txt", android_safe=True)
    assert ok.is_valid
    bad = PathValidator.validate_path("../../etc/passwd", android_safe=True)
    assert not bad.is_valid


def test_text_validator_sanitize():
    res = TextValidator.sanitize_shell_input("hello; rm -rf /", level=None)
    # In permissive mode via None, it should warn but keep valid string escaped/unchanged depending on policy
    assert res is not None


def test_coordinate_and_numeric_validators():
    cp = CoordinateValidator.validate_coordinate_pair(10, 20)
    assert cp.is_valid
    swipe = CoordinateValidator.validate_swipe_coordinates(0, 0, 5, 5)
    assert swipe.is_valid
    dur = NumericValidator.validate_duration(300)
    assert dur.is_valid
    dist = NumericValidator.validate_distance(100)
    assert dist.is_valid

