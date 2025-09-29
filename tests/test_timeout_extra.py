import asyncio
import pytest

from src.timeout import start_deadline, remaining_time, stage_budget


@pytest.mark.asyncio
async def test_stage_budget_respects_cap_without_deadline():
    # Without an active deadline, stage_budget uses default then applies the cap
    # 50% of default(3.0) = 1.5, but cap=0.4 should limit it to 0.4
    value = stage_budget(0.5, cap=0.4, default=3.0)
    assert 0.39 < value <= 0.4


@pytest.mark.asyncio
async def test_remaining_time_floor_after_deadline_passes():
    # After the deadline elapses, remaining_time should never go below the floor
    async with start_deadline(0.05):
        # Sleep just beyond the deadline to force remaining time to the floor
        await asyncio.sleep(0.07)
        rem = remaining_time()
        # Default floor is 0.05 seconds
        assert rem >= 0.05
        # And stage_budget should also respect the same minimum
        sb = stage_budget(1.0)
        assert sb >= 0.05

