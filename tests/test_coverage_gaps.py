"""Tests to cover remaining gaps for CI coverage threshold."""

import pytest

from src.error_handler import (
    AndroidMCPError,
    ErrorCode,
    ErrorHandler,
    format_error_response,
    get_recovery_suggestions,
)


class TestErrorHandlerCoverageGaps:
    """Cover uncovered paths in error_handler.py."""

    def test_get_default_message_known_codes(self):
        """Test _get_default_message for known error codes."""
        handler = ErrorHandler()
        msg = handler._get_default_message(ErrorCode.NO_DEVICES_FOUND)
        assert "No Android devices" in msg

        msg = handler._get_default_message(ErrorCode.DEVICE_OFFLINE)
        assert "offline" in msg

        msg = handler._get_default_message(ErrorCode.ADB_TIMEOUT)
        assert "timed out" in msg

        msg = handler._get_default_message(ErrorCode.UI_DUMP_FAILED)
        assert "UI layout" in msg

        msg = handler._get_default_message(ErrorCode.ELEMENT_NOT_FOUND)
        assert "element" in msg.lower()

        msg = handler._get_default_message(ErrorCode.SCREENSHOT_FAILED)
        assert "screenshot" in msg.lower()

        msg = handler._get_default_message(ErrorCode.INVALID_PARAMETER)
        assert "parameter" in msg.lower()

    def test_get_default_message_unknown_code(self):
        """Test _get_default_message for codes not in the map."""
        handler = ErrorHandler()
        msg = handler._get_default_message(ErrorCode.ADB_COMMAND_FAILED)
        assert "ADB_1200" in msg

    @pytest.mark.asyncio
    async def test_wrap_async_operation_passthrough_dict(self):
        """Test wrap_async_operation when func returns dict with 'success'."""
        handler = ErrorHandler()

        @handler.wrap_async_operation("test_op")
        async def returns_dict():
            return {"success": True, "data": "hello"}

        result = await returns_dict()
        assert result["success"] is True
        assert result["data"] == "hello"

    def test_recovery_suggestions_timeout_context(self):
        """Test contextual suggestions for timeout context."""
        suggestions = get_recovery_suggestions(
            ErrorCode.ADB_TIMEOUT, context={"timeout": 30}
        )
        assert any("timeout" in s.lower() for s in suggestions)

    def test_recovery_suggestions_permission_context(self):
        """Test contextual suggestions for permission context."""
        suggestions = get_recovery_suggestions(
            ErrorCode.ADB_COMMAND_FAILED,
            context={"details": "permission denied"},
        )
        assert any("permission" in s.lower() for s in suggestions)

    def test_recovery_suggestions_storage_context(self):
        """Test contextual suggestions for storage context."""
        suggestions = get_recovery_suggestions(
            ErrorCode.SCREENSHOT_FAILED,
            context={"details": "no storage space left"},
        )
        assert any("storage" in s.lower() for s in suggestions)

    def test_format_error_with_custom_recovery(self):
        """Test handle_error with custom recovery_suggestions on error."""
        handler = ErrorHandler()
        error = AndroidMCPError(
            ErrorCode.UNKNOWN_ERROR,
            "custom error",
            recovery_suggestions=["Try restarting"],
        )
        result = handler.handle_error(error)
        assert result["success"] is False
        assert len(result["recovery_suggestions"]) > 0

    def test_format_error_response_fallback_recovery(self):
        """Test format_error_response fallback to error's recovery_suggestions."""
        error = AndroidMCPError(
            ErrorCode.UNKNOWN_ERROR,
            "obscure error",
            recovery_suggestions=["Custom suggestion"],
        )
        # Pass a context that won't match any contextual suggestions
        result = format_error_response(error)
        assert result["success"] is False
        assert "recovery_suggestions" in result


class TestDeviceToolRegistration:
    """Cover register_device_tools function."""

    def test_register_device_tools(self):
        """Test that register_device_tools registers all tools."""
        from unittest.mock import MagicMock

        from src.tools.device import register_device_tools

        mock_mcp = MagicMock()
        # Make tool() return a callable decorator
        mock_mcp.tool.return_value = lambda f: f

        register_device_tools(mock_mcp)

        # Should have registered 3 tools
        assert mock_mcp.tool.call_count == 3
