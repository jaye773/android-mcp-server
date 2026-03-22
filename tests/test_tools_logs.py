"""Dedicated unit tests for src/tools/logs.py.

Covers all 4 tool functions:
  - get_logcat: happy path, missing component, exception
  - start_log_monitoring: happy path, path traversal validation, missing component, exception
  - stop_log_monitoring: happy path, identifier validation, missing component, exception
  - list_active_monitors: happy path, missing component, exception
  - register_log_tools wiring
"""

import pytest
from unittest.mock import MagicMock

from src.tools.logs import (
    get_logcat,
    list_active_monitors,
    register_log_tools,
    start_log_monitoring,
    stop_log_monitoring,
)
from src.tool_models import LogcatParams, LogMonitorParams, StopMonitorParams
from src.registry import ComponentRegistry


@pytest.fixture(autouse=True)
def _clean_registry():
    ComponentRegistry.reset()
    yield
    ComponentRegistry.reset()


# ---------------------------------------------------------------------------
# get_logcat
# ---------------------------------------------------------------------------


class TestGetLogcat:
    @pytest.mark.asyncio
    async def test_happy_path(self, mock_log_monitor):
        ComponentRegistry.instance().register("log_monitor", mock_log_monitor)

        params = LogcatParams(tag_filter="MyApp", priority="I", max_lines=50)
        result = await get_logcat(params)

        assert result["success"] is True
        assert "logs" in result
        mock_log_monitor.get_logcat.assert_awaited_once_with(
            tag_filter="MyApp", priority="I", max_lines=50, clear_first=False
        )

    @pytest.mark.asyncio
    async def test_defaults(self, mock_log_monitor):
        ComponentRegistry.instance().register("log_monitor", mock_log_monitor)

        params = LogcatParams()
        result = await get_logcat(params)

        assert result["success"] is True
        mock_log_monitor.get_logcat.assert_awaited_once_with(
            tag_filter=None, priority="V", max_lines=100, clear_first=False
        )

    @pytest.mark.asyncio
    async def test_missing_component(self):
        params = LogcatParams()
        result = await get_logcat(params)

        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_exception(self, mock_log_monitor):
        ComponentRegistry.instance().register("log_monitor", mock_log_monitor)
        mock_log_monitor.get_logcat.side_effect = RuntimeError("logcat fail")

        params = LogcatParams()
        result = await get_logcat(params)

        assert result["success"] is False
        assert "logcat fail" in result["error"]


# ---------------------------------------------------------------------------
# start_log_monitoring
# ---------------------------------------------------------------------------


class TestStartLogMonitoring:
    @pytest.mark.asyncio
    async def test_happy_path(self, mock_log_monitor):
        ComponentRegistry.instance().register("log_monitor", mock_log_monitor)

        params = LogMonitorParams(tag_filter="MyApp", priority="D")
        result = await start_log_monitoring(params)

        assert result["success"] is True
        mock_log_monitor.start_log_monitoring.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_output_file_valid(self, mock_log_monitor):
        ComponentRegistry.instance().register("log_monitor", mock_log_monitor)

        params = LogMonitorParams(output_file="myapp.log")
        result = await start_log_monitoring(params)

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_output_file_path_traversal(self, mock_log_monitor):
        """Path traversal in output_file should be rejected."""
        ComponentRegistry.instance().register("log_monitor", mock_log_monitor)

        params = LogMonitorParams(output_file="../../etc/passwd")
        result = await start_log_monitoring(params)

        assert result["success"] is False
        assert "Validation failed" in result["error"]
        mock_log_monitor.start_log_monitoring.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_component(self):
        params = LogMonitorParams()
        result = await start_log_monitoring(params)

        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_exception(self, mock_log_monitor):
        ComponentRegistry.instance().register("log_monitor", mock_log_monitor)
        mock_log_monitor.start_log_monitoring.side_effect = RuntimeError("monitor start fail")

        params = LogMonitorParams()
        result = await start_log_monitoring(params)

        assert result["success"] is False
        assert "monitor start fail" in result["error"]


# ---------------------------------------------------------------------------
# stop_log_monitoring
# ---------------------------------------------------------------------------


class TestStopLogMonitoring:
    @pytest.mark.asyncio
    async def test_happy_path(self, mock_log_monitor):
        ComponentRegistry.instance().register("log_monitor", mock_log_monitor)

        params = StopMonitorParams(monitor_id="monitor_001")
        result = await stop_log_monitoring(params)

        assert result["success"] is True
        mock_log_monitor.stop_log_monitoring.assert_awaited_once_with(monitor_id="monitor_001")

    @pytest.mark.asyncio
    async def test_stop_all(self, mock_log_monitor):
        """No monitor_id -> stop all monitors."""
        ComponentRegistry.instance().register("log_monitor", mock_log_monitor)

        params = StopMonitorParams()
        result = await stop_log_monitoring(params)

        assert result["success"] is True
        mock_log_monitor.stop_log_monitoring.assert_awaited_once_with(monitor_id=None)

    @pytest.mark.asyncio
    async def test_identifier_validation_failure(self, mock_log_monitor):
        """Shell metacharacters in monitor_id should be rejected."""
        ComponentRegistry.instance().register("log_monitor", mock_log_monitor)

        params = StopMonitorParams(monitor_id="monitor; rm -rf /")
        result = await stop_log_monitoring(params)

        assert result["success"] is False
        assert "Validation failed" in result["error"]
        mock_log_monitor.stop_log_monitoring.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_component(self):
        params = StopMonitorParams()
        result = await stop_log_monitoring(params)

        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_exception(self, mock_log_monitor):
        ComponentRegistry.instance().register("log_monitor", mock_log_monitor)
        mock_log_monitor.stop_log_monitoring.side_effect = RuntimeError("stop fail")

        params = StopMonitorParams(monitor_id="monitor_001")
        result = await stop_log_monitoring(params)

        assert result["success"] is False
        assert "stop fail" in result["error"]


# ---------------------------------------------------------------------------
# list_active_monitors
# ---------------------------------------------------------------------------


class TestListActiveMonitors:
    @pytest.mark.asyncio
    async def test_happy_path(self, mock_log_monitor):
        ComponentRegistry.instance().register("log_monitor", mock_log_monitor)

        result = await list_active_monitors()

        assert result["success"] is True
        mock_log_monitor.list_active_monitors.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_missing_component(self):
        result = await list_active_monitors()

        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_exception(self, mock_log_monitor):
        ComponentRegistry.instance().register("log_monitor", mock_log_monitor)
        mock_log_monitor.list_active_monitors.side_effect = RuntimeError("list fail")

        result = await list_active_monitors()

        assert result["success"] is False
        assert "list fail" in result["error"]


# ---------------------------------------------------------------------------
# register_log_tools
# ---------------------------------------------------------------------------


class TestRegisterLogTools:
    def test_registers_four_tools(self):
        mcp = MagicMock()
        mcp.tool.return_value = lambda fn: fn

        register_log_tools(mcp)

        assert mcp.tool.call_count == 4
