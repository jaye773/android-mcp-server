"""Tests to cover remaining gaps for CI coverage threshold."""


class TestDeviceToolRegistration:
    """Cover register_device_tools function."""

    def test_register_device_tools(self):
        """Test that register_device_tools registers all tools."""
        from unittest.mock import MagicMock

        from src.tools.device import register_device_tools

        mock_mcp = MagicMock()
        # Make tool() return a callable decorator
        mock_mcp.tool.return_value = lambda f: f

        components = {"adb_manager": MagicMock()}
        register_device_tools(mock_mcp, components)

        # Should have registered 3 tools
        assert mock_mcp.tool.call_count == 3
