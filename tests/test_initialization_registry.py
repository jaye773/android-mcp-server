"""Tests for initialization.py and registry.py failure paths."""

import logging
from unittest.mock import AsyncMock, patch

import pytest

from src.initialization import initialize_components
from src.registry import ComponentRegistry


class TestInitializationPartialFailures:
    """Test partial initialization failures where some components fail."""

    @pytest.mark.asyncio
    async def test_ui_inspector_construction_fails(self, mock_registry):
        """ADB succeeds but UILayoutExtractor construction raises."""
        with (
            patch("src.initialization.ADBManager") as mock_adb_cls,
            patch("src.initialization.UILayoutExtractor") as mock_ui_cls,
        ):
            mock_adb = AsyncMock()
            mock_adb.auto_select_device.return_value = {
                "success": True,
                "selected": {"id": "emulator-5554"},
            }
            mock_adb_cls.return_value = mock_adb
            mock_ui_cls.side_effect = RuntimeError("uiautomator unavailable")

            with pytest.raises(RuntimeError, match="uiautomator unavailable"):
                await initialize_components()

    @pytest.mark.asyncio
    async def test_screen_interactor_construction_fails(self, mock_registry):
        """ADB and UI inspector ok, but ScreenAutomation raises."""
        with (
            patch("src.initialization.ADBManager") as mock_adb_cls,
            patch("src.initialization.UILayoutExtractor") as mock_ui_cls,
            patch("src.initialization.ScreenAutomation") as mock_screen_cls,
        ):
            mock_adb = AsyncMock()
            mock_adb.auto_select_device.return_value = {
                "success": True,
                "selected": {"id": "emulator-5554"},
            }
            mock_adb_cls.return_value = mock_adb
            mock_ui_cls.return_value = AsyncMock()
            mock_screen_cls.side_effect = TypeError("bad argument")

            with pytest.raises(TypeError, match="bad argument"):
                await initialize_components()

    @pytest.mark.asyncio
    async def test_log_monitor_construction_fails(self, mock_registry):
        """Late-stage component failure (LogMonitor) propagates."""
        with (
            patch("src.initialization.ADBManager") as mock_adb_cls,
            patch("src.initialization.UILayoutExtractor"),
            patch("src.initialization.ScreenAutomation"),
            patch("src.initialization.MediaCapture"),
            patch("src.initialization.VideoRecorder"),
            patch("src.initialization.LogMonitor") as mock_log_cls,
        ):
            mock_adb = AsyncMock()
            mock_adb.auto_select_device.return_value = {
                "success": True,
                "selected": {"id": "emulator-5554"},
            }
            mock_adb_cls.return_value = mock_adb
            mock_log_cls.side_effect = OSError("cannot access logcat")

            with pytest.raises(OSError, match="cannot access logcat"):
                await initialize_components()


class TestInitializationNoDevices:
    """Test auto-device selection when no devices are available."""

    @pytest.mark.asyncio
    async def test_auto_select_no_devices_continues(self, mock_registry):
        """When auto_select_device returns success=False, init still proceeds."""
        with (
            patch("src.initialization.ADBManager") as mock_adb_cls,
            patch("src.initialization.UILayoutExtractor"),
            patch("src.initialization.ScreenAutomation"),
            patch("src.initialization.MediaCapture"),
            patch("src.initialization.VideoRecorder"),
            patch("src.initialization.LogMonitor"),
        ):
            mock_adb = AsyncMock()
            mock_adb.auto_select_device.return_value = {
                "success": False,
                "error": "No devices connected",
            }
            mock_adb_cls.return_value = mock_adb

            # Should succeed — no-device is a warning, not an error
            components = await initialize_components()

            assert "adb_manager" in components
            assert "ui_inspector" in components
            # 6 components (adb, ui, screen_automation, media, video, log) + validator
            assert len(components) == 7

    @pytest.mark.asyncio
    async def test_auto_select_no_devices_logs_warning(self, mock_registry, caplog):
        """Verify a warning is logged when no device is available."""
        with (
            patch("src.initialization.ADBManager") as mock_adb_cls,
            patch("src.initialization.UILayoutExtractor"),
            patch("src.initialization.ScreenAutomation"),
            patch("src.initialization.MediaCapture"),
            patch("src.initialization.VideoRecorder"),
            patch("src.initialization.LogMonitor"),
        ):
            mock_adb = AsyncMock()
            mock_adb.auto_select_device.return_value = {
                "success": False,
                "error": "No devices connected",
            }
            mock_adb_cls.return_value = mock_adb

            with caplog.at_level(logging.WARNING, logger="src.initialization"):
                await initialize_components()

            assert any("No devices available" in r.message for r in caplog.records)


class TestInitializationRegistryPopulation:
    """Verify initialize_components populates the ComponentRegistry."""

    @pytest.mark.asyncio
    async def test_registry_populated_after_init(self, mock_registry):
        """All components accessible via the singleton after init."""
        with (
            patch("src.initialization.ADBManager") as mock_adb_cls,
            patch("src.initialization.UILayoutExtractor"),
            patch("src.initialization.ScreenAutomation"),
            patch("src.initialization.MediaCapture"),
            patch("src.initialization.VideoRecorder"),
            patch("src.initialization.LogMonitor"),
        ):
            mock_adb = AsyncMock()
            mock_adb.auto_select_device.return_value = {
                "success": True,
                "selected": {"id": "emulator-5554"},
            }
            mock_adb_cls.return_value = mock_adb

            await initialize_components()

            registry = ComponentRegistry.instance()
            for key in [
                "adb_manager",
                "ui_inspector",
                "screen_automation",
                "media_capture",
                "video_recorder",
                "log_monitor",
                "validator",
            ]:
                assert registry.get(key) is not None, f"Missing component: {key}"

    @pytest.mark.asyncio
    async def test_registry_not_populated_on_failure(self, mock_registry):
        """If init raises, the registry should remain empty."""
        with patch("src.initialization.ADBManager") as mock_adb_cls:
            mock_adb_cls.side_effect = RuntimeError("boom")

            with pytest.raises(RuntimeError):
                await initialize_components()

        registry = ComponentRegistry.instance()
        assert registry.get("adb_manager") is None
        assert registry.get("validator") is None


class TestInitializationLogging:
    """Verify initialization logging on success and failure."""

    @pytest.mark.asyncio
    async def test_success_log_message(self, mock_registry, caplog):
        """Successful init logs 'All components initialized successfully'."""
        with (
            patch("src.initialization.ADBManager") as mock_adb_cls,
            patch("src.initialization.UILayoutExtractor"),
            patch("src.initialization.ScreenAutomation"),
            patch("src.initialization.MediaCapture"),
            patch("src.initialization.VideoRecorder"),
            patch("src.initialization.LogMonitor"),
        ):
            mock_adb = AsyncMock()
            mock_adb.auto_select_device.return_value = {
                "success": True,
                "selected": {"id": "emulator-5554"},
            }
            mock_adb_cls.return_value = mock_adb

            with caplog.at_level(logging.INFO, logger="src.initialization"):
                await initialize_components()

            assert any(
                "All components initialized successfully" in r.message
                for r in caplog.records
            )

    @pytest.mark.asyncio
    async def test_failure_log_message(self, mock_registry, caplog):
        """Failed init logs 'Component initialization failed'."""
        with patch("src.initialization.ADBManager") as mock_adb_cls:
            mock_adb_cls.side_effect = RuntimeError("startup failed")

            with caplog.at_level(logging.ERROR, logger="src.initialization"):
                with pytest.raises(RuntimeError):
                    await initialize_components()

            assert any(
                "Component initialization failed" in r.message
                for r in caplog.records
            )


class TestComponentRegistrySingleton:
    """Test singleton behavior of ComponentRegistry."""

    def test_instance_returns_same_object(self):
        """Repeated calls to instance() return the same registry."""
        ComponentRegistry.reset()
        a = ComponentRegistry.instance()
        b = ComponentRegistry.instance()
        assert a is b
        ComponentRegistry.reset()

    def test_reset_creates_new_instance(self):
        """After reset(), instance() returns a fresh registry."""
        ComponentRegistry.reset()
        first = ComponentRegistry.instance()
        first.register("x", "value")

        ComponentRegistry.reset()
        second = ComponentRegistry.instance()

        assert first is not second
        assert second.get("x") is None
        ComponentRegistry.reset()

    def test_reset_clears_registered_components(self):
        """Reset discards all registered components."""
        ComponentRegistry.reset()
        reg = ComponentRegistry.instance()
        reg.register("a", 1)
        reg.register("b", 2)

        ComponentRegistry.reset()
        reg = ComponentRegistry.instance()

        assert reg.get("a") is None
        assert reg.get("b") is None
        ComponentRegistry.reset()

    def test_concurrent_instance_access(self):
        """Multiple threads calling instance() get the same singleton."""
        ComponentRegistry.reset()
        results = []

        def grab_instance():
            results.append(ComponentRegistry.instance())

        import threading

        threads = [threading.Thread(target=grab_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should be the same object (singleton guarantee)
        assert all(r is results[0] for r in results)
        ComponentRegistry.reset()


class TestComponentRegistryLookup:
    """Test registry get / register / register_all methods."""

    def test_get_missing_returns_none(self):
        """Requesting a non-existent key returns None, not an error."""
        ComponentRegistry.reset()
        reg = ComponentRegistry.instance()

        assert reg.get("nonexistent") is None
        assert reg.get("") is None
        assert reg.get("adb_manager") is None
        ComponentRegistry.reset()

    def test_register_single(self):
        """register() makes a component retrievable via get()."""
        ComponentRegistry.reset()
        reg = ComponentRegistry.instance()

        sentinel = object()
        reg.register("my_component", sentinel)

        assert reg.get("my_component") is sentinel
        ComponentRegistry.reset()

    def test_register_all_bulk(self):
        """register_all() registers every item in the dict."""
        ComponentRegistry.reset()
        reg = ComponentRegistry.instance()

        components = {"a": 1, "b": 2, "c": 3}
        reg.register_all(components)

        assert reg.get("a") == 1
        assert reg.get("b") == 2
        assert reg.get("c") == 3
        ComponentRegistry.reset()

    def test_register_overwrites_existing(self):
        """Registering the same name twice overwrites the first."""
        ComponentRegistry.reset()
        reg = ComponentRegistry.instance()

        reg.register("x", "first")
        reg.register("x", "second")

        assert reg.get("x") == "second"
        ComponentRegistry.reset()

    def test_register_all_overwrites_existing(self):
        """register_all merges into existing, overwriting collisions."""
        ComponentRegistry.reset()
        reg = ComponentRegistry.instance()

        reg.register("keep", "original")
        reg.register("replace", "old")
        reg.register_all({"replace": "new", "added": "fresh"})

        assert reg.get("keep") == "original"
        assert reg.get("replace") == "new"
        assert reg.get("added") == "fresh"
        ComponentRegistry.reset()

    def test_register_all_empty_dict(self):
        """register_all with an empty dict is a no-op."""
        ComponentRegistry.reset()
        reg = ComponentRegistry.instance()

        reg.register("pre", 1)
        reg.register_all({})

        assert reg.get("pre") == 1
        ComponentRegistry.reset()


class TestComponentRegistryLogging:
    """Verify registry debug logging."""

    def test_register_all_logs_component_names(self, caplog):
        """register_all emits a DEBUG log listing component names."""
        ComponentRegistry.reset()
        reg = ComponentRegistry.instance()

        with caplog.at_level(logging.DEBUG, logger="src.registry"):
            reg.register_all({"alpha": 1, "beta": 2})

        assert any("Registered 2 component(s)" in r.message for r in caplog.records)
        assert any("alpha" in r.message for r in caplog.records)
        assert any("beta" in r.message for r in caplog.records)
        ComponentRegistry.reset()
