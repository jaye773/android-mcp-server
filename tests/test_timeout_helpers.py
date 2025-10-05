import asyncio

import pytest

from src.timeout import (
    get_deadline,
    has_deadline,
    remaining_time,
    stage_budget,
    start_deadline,
)


@pytest.mark.asyncio
async def test_deadline_basic_remaining_and_flags():
    assert has_deadline() is False
    assert get_deadline() is None
    # Without deadline, remaining_time returns default
    default = remaining_time(default=1.23)
    assert default >= 1.23

    async with start_deadline(0.2):
        assert has_deadline() is True
        assert get_deadline() is not None
        rem1 = remaining_time()
        assert rem1 > 0
        # stage_budget returns a fraction of remaining
        frac = stage_budget(0.5)
        assert 0 < frac <= rem1


@pytest.mark.asyncio
async def test_deadline_enforcement_with_asyncio_timeout():
    async with start_deadline(0.1):
        with pytest.raises(asyncio.TimeoutError):
            async with asyncio.timeout(0.05):
                await asyncio.sleep(0.2)
