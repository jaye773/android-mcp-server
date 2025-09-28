"""Stub stdio transport for offline testing."""

import contextlib
from typing import AsyncIterator, Tuple

from .. import ClientSession, StdioServerParameters


@contextlib.asynccontextmanager
async def stdio_client(
    params: StdioServerParameters,
) -> AsyncIterator[Tuple[object, object]]:
    """Yield dummy reader/writer pair for compatibility."""

    dummy_reader = object()
    dummy_writer = object()
    yield (dummy_reader, dummy_writer)
