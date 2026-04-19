"""Tests for the timeout_wrapper and mcp_error_boundary decorators."""

import asyncio
import logging

import pytest

from src.decorators import mcp_error_boundary, timeout_wrapper


@pytest.mark.asyncio
async def test_timeout_wrapper_success():
    """Test that timeout_wrapper returns result on success."""

    @timeout_wrapper(timeout_seconds=5)
    async def fast_func():
        return {"success": True, "data": "ok"}

    result = await fast_func()
    assert result["success"] is True
    assert result["data"] == "ok"


@pytest.mark.asyncio
async def test_timeout_wrapper_timeout():
    """Test that timeout_wrapper handles timeout."""

    @timeout_wrapper(timeout_seconds=0.01)
    async def slow_func():
        await asyncio.sleep(10)
        return {"success": True}

    result = await slow_func()
    assert result["success"] is False
    assert result["error_code"] == "OPERATION_TIMEOUT"
    assert "timed out" in result["error"]
    assert result["timeout_seconds"] == 0.01
    assert "elapsed_seconds" in result
    assert "recovery_suggestions" in result


@pytest.mark.asyncio
async def test_timeout_wrapper_exception():
    """Test that timeout_wrapper handles generic exceptions."""

    @timeout_wrapper(timeout_seconds=5)
    async def failing_func():
        raise ValueError("something broke")

    result = await failing_func()
    assert result["success"] is False
    assert result["error_code"] == "TOOL_EXECUTION_ERROR"
    assert "something broke" in result["error"]


class TestMcpErrorBoundary:
    """Tests for the @mcp_error_boundary decorator."""

    @pytest.mark.asyncio
    async def test_wraps_exception_into_envelope(self):
        """Decorator converts a raised RuntimeError to a standard error envelope."""

        @mcp_error_boundary()
        async def boom():
            raise RuntimeError("kaboom")

        result = await boom()
        assert result == {
            "success": False,
            "error": "kaboom",
            "operation": "boom",
        }

    @pytest.mark.asyncio
    async def test_passthrough_on_success(self):
        """Return value is unchanged on the success path."""

        @mcp_error_boundary()
        async def ok():
            return {"success": True, "data": [1, 2, 3]}

        result = await ok()
        assert result == {"success": True, "data": [1, 2, 3]}

    @pytest.mark.asyncio
    async def test_operation_name_override(self):
        """Explicit operation="foo" propagates into the error envelope."""

        @mcp_error_boundary(operation="custom_op")
        async def named():
            raise ValueError("bad input")

        result = await named()
        assert result["operation"] == "custom_op"
        assert result["success"] is False
        assert "bad input" in result["error"]

    @pytest.mark.asyncio
    async def test_logs_unhandled_exception(self, caplog):
        """logger.exception is called when a tool raises."""

        @mcp_error_boundary()
        async def raises():
            raise RuntimeError("explode")

        with caplog.at_level(logging.ERROR, logger="src.decorators"):
            result = await raises()

        assert result["success"] is False
        # logger.exception emits at ERROR level and attaches exc_info.
        matching = [
            rec
            for rec in caplog.records
            if rec.name == "src.decorators"
            and "Unhandled error in raises" in rec.getMessage()
        ]
        assert matching, "expected logger.exception to record the unhandled error"
        assert matching[0].exc_info is not None
