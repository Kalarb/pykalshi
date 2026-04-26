"""Tests for pykalshi.rate_limiter."""

import pytest
from pykalshi.rate_limiter import ReadWriteTokenBucket


class TestReadWriteTokenBucket:
    @pytest.mark.asyncio
    async def test_initial_tokens(self) -> None:
        bucket = ReadWriteTokenBucket(read_rate=10.0, write_rate=5.0)
        assert bucket.read_tokens == 10.0
        assert bucket.write_tokens == 5.0

    @pytest.mark.asyncio
    async def test_read_acquire_consumes_read_tokens(self) -> None:
        bucket = ReadWriteTokenBucket(read_rate=10.0, write_rate=5.0)
        await bucket.acquire(global_cost=1.0, write_cost=0.0)
        assert bucket.read_tokens == 9.0
        assert bucket.write_tokens == 5.0  # write unchanged

    @pytest.mark.asyncio
    async def test_write_acquire_consumes_write_tokens(self) -> None:
        bucket = ReadWriteTokenBucket(read_rate=10.0, write_rate=5.0)
        await bucket.acquire(global_cost=1.0, write_cost=1.0)
        assert bucket.write_tokens == 4.0
        assert bucket.read_tokens == 10.0  # read unchanged

    @pytest.mark.asyncio
    async def test_try_acquire_success(self) -> None:
        bucket = ReadWriteTokenBucket(read_rate=10.0, write_rate=5.0)
        result = await bucket.try_acquire(global_cost=1.0, write_cost=0.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_try_acquire_insufficient_tokens(self) -> None:
        bucket = ReadWriteTokenBucket(read_rate=1.0, write_rate=1.0)
        await bucket.acquire(global_cost=1.0, write_cost=0.0)
        result = await bucket.try_acquire(global_cost=1.0, write_cost=0.0)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_wait_time_immediate(self) -> None:
        bucket = ReadWriteTokenBucket(read_rate=10.0, write_rate=5.0)
        wait = await bucket.get_wait_time(global_cost=1.0, write_cost=0.0)
        assert wait == 0.0

    @pytest.mark.asyncio
    async def test_reconfigure(self) -> None:
        bucket = ReadWriteTokenBucket(read_rate=10.0, write_rate=5.0)
        await bucket.reconfigure(read_rate=20.0, write_rate=10.0)
        assert bucket.read_capacity == 20.0
        assert bucket.write_capacity == 10.0

    @pytest.mark.asyncio
    async def test_reconfigure_invalid(self) -> None:
        bucket = ReadWriteTokenBucket(read_rate=10.0, write_rate=5.0)
        with pytest.raises(ValueError, match="positive"):
            await bucket.reconfigure(read_rate=-1.0, write_rate=5.0)

    def test_invalid_rates(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            ReadWriteTokenBucket(read_rate=0.0, write_rate=5.0)

    @pytest.mark.asyncio
    async def test_exceed_capacity_raises(self) -> None:
        bucket = ReadWriteTokenBucket(read_rate=5.0, write_rate=3.0)
        with pytest.raises(ValueError, match="exceeds"):
            await bucket.acquire(global_cost=6.0, write_cost=0.0)
        with pytest.raises(ValueError, match="exceeds"):
            await bucket.acquire(global_cost=1.0, write_cost=4.0)

    def test_get_status(self) -> None:
        bucket = ReadWriteTokenBucket(read_rate=10.0, write_rate=5.0)
        status = bucket.get_status()
        assert status["type"] == "ReadWriteTokenBucket"
        assert status["read_tokens"] == 10.0
        assert status["write_tokens"] == 5.0
