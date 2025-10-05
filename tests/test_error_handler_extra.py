"""Extra tests for error_handler to boost coverage on debug and wrappers."""

import pytest

from src.error_handler import (
    AndroidMCPError,
    ErrorCode,
    ErrorHandler,
)


def test_create_error_response_android_mcp_with_debug():
    handler = ErrorHandler()

    err = AndroidMCPError(
        ErrorCode.DEVICE_OFFLINE,
        "Device is offline",
        details={"device_id": "emulator-5554"},
        recovery_suggestions=["Reconnect USB"],
    )

    res = handler.create_error_response(err, include_debug=True)
    assert res["success"] is False
    assert res["error_code"] == ErrorCode.DEVICE_OFFLINE.value
    # Context from error should be included
    assert res["context"]["device_id"] == "emulator-5554"
    # Debug info branch is exercised
    assert "debug_info" in res


def test_create_error_response_error_code_with_context_and_suggestion():
    handler = ErrorHandler()
    res = handler.create_error_response(
        ErrorCode.ADB_TIMEOUT,
        message="Timed out",
        context={"operation": "exec"},
        recovery_suggestion="Increase timeout",
    )
    assert res["error_code"] == ErrorCode.ADB_TIMEOUT.value
    assert res["error"] == "Timed out"
    assert res["context"]["operation"] == "exec"
    assert res["severity"] == "medium"
    assert res["recovery_suggestion"] == "Increase timeout"


def test_create_error_response_generic_exception_with_debug_and_context():
    handler = ErrorHandler()
    try:
        raise ValueError("bad value")
    except Exception as e:
        res = handler.create_error_response(
            e, message=None, context={"foo": "bar"}, include_debug=True
        )
    assert res["error_code"] == ErrorCode.UNKNOWN_ERROR.value
    assert res["severity"] == "high"
    assert res["context"]["foo"] == "bar"
    assert "debug_info" in res


@pytest.mark.asyncio
async def test_wrap_async_operation_success_and_errors():
    handler = ErrorHandler()

    @handler.wrap_async_operation("compute")
    async def returns_value():
        return 21 * 2

    @handler.wrap_async_operation("failing_android_error")
    async def raises_android_error():
        raise AndroidMCPError(ErrorCode.UI_DUMP_FAILED, "dump failed")

    @handler.wrap_async_operation("generic_fail")
    async def raises_generic():
        raise RuntimeError("boom")

    ok = await returns_value()
    assert ok["success"] is True
    assert ok["result"] == 42
    assert "message" in ok  # from create_success_response

    e1 = await raises_android_error()
    assert e1["success"] is False
    assert e1["error_code"] == ErrorCode.UI_DUMP_FAILED.value

    e2 = await raises_generic()
    assert e2["success"] is False
    assert e2["error_code"] == ErrorCode.UNKNOWN_ERROR.value
    assert "generic_fail" in e2["error"]

