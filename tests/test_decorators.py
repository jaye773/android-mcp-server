"""Tests for the timeout_wrapper decorator."""

import asyncio

import pytest

from src.decorators import timeout_wrapper


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
