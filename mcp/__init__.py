"""Minimal stub of the mcp package for testing without external dependency."""

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Dict, List, Optional


@dataclass
class StdioServerParameters:
    """Lightweight container for stdio server configuration."""

    command: str
    args: List[str] | None = None

    def __post_init__(self):
        if self.args is None:
            self.args = []


class ClientSession:
    """Simplified async context manager mimicking mcp.ClientSession."""

    def __init__(self, reader: object | None = None, writer: object | None = None):
        self.reader = reader
        self.writer = writer

    async def __aenter__(self) -> "ClientSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - simple cleanup
        return None

    async def initialize(self) -> Dict[str, Any]:
        return {"success": True}

    async def list_tools(self) -> SimpleNamespace:
        return SimpleNamespace(tools=[])

    async def call_tool(
        self, name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> SimpleNamespace:
        raise NotImplementedError("ClientSession stub cannot call remote tools")
