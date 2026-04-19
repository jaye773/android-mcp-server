"""Singleton component registry for dependency injection."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ComponentRegistry:
    """Singleton registry that replaces per-module global ``_components`` dicts.

    Usage::

        # During initialisation (server.py / initialization.py)
        registry = ComponentRegistry.instance()
        registry.register_all(components_dict)

        # Inside any tool module
        adb = ComponentRegistry.instance().get("adb_manager")
    """

    _instance: Optional[ComponentRegistry] = None

    def __init__(self) -> None:
        """Initialize empty component registry."""
        self._components: Dict[str, Any] = {}

    # -- singleton helpers ---------------------------------------------------

    @classmethod
    def instance(cls) -> ComponentRegistry:
        """Return (or create) the singleton."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Discard the singleton.  Primarily for tests."""
        cls._instance = None

    # -- registration --------------------------------------------------------

    def register_all(self, components: Dict[str, Any]) -> None:
        """Bulk-register components from a dict."""
        self._components.update(components)
        logger.debug(
            "Registered %d component(s): %s",
            len(components),
            ", ".join(sorted(components)),
        )

    def register(self, name: str, component: Any) -> None:
        """Register a single component."""
        self._components[name] = component

    # -- access --------------------------------------------------------------

    def get(self, name: str) -> Optional[Any]:
        """Look up a component by name (returns *None* if missing)."""
        return self._components.get(name)
