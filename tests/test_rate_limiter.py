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
        await bucket.acquire(read_cost=1.0, write_cost=0.0)
        assert bucket.read_tokens == 9.0
        assert bucket.write_tokens == 5.0  # write unchanged

    @pytest.mark.asyncio
    async def test_write_acquire_consumes_write_tokens(self) -> None:
        bucket = ReadWriteTokenBucket(read_rate=10.0, write_rate=5.0)
        await bucket.acquire(read_cost=1.0, write_cost=1.0)
        assert bucket.write_tokens == 4.0
        assert bucket.read_tokens == 10.0  # read unchanged

    @pytest.mark.asyncio
    async def test_try_acquire_success(self) -> None:
        bucket = ReadWriteTokenBucket(read_rate=10.0, write_rate=5.0)
        result = await bucket.try_acquire(read_cost=1.0, write_cost=0.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_try_acquire_insufficient_tokens(self) -> None:
        bucket = ReadWriteTokenBucket(read_rate=1.0, write_rate=1.0)
        await bucket.acquire(read_cost=1.0, write_cost=0.0)
        result = await bucket.try_acquire(read_cost=1.0, write_cost=0.0)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_wait_time_immediate(self) -> None:
        bucket = ReadWriteTokenBucket(read_rate=10.0, write_rate=5.0)
        wait = await bucket.get_wait_time(read_cost=1.0, write_cost=0.0)
        assert wait == 0.0

    @pytest.mark.asyncio
    async def test_reconfigure(self) -> None:
        bucket = ReadWriteTokenBucket(read_rate=10.0, write_rate=5.0)
        await bucket.reconfigure(read_rate=20.0, write_rate=10.0)
        assert bucket.read_capacity == 20.0
        assert bucket.write_capacity == 10.0

    @pytest.mark.asyncio
    async def test_reconfigure_with_capacity(self) -> None:
        bucket = ReadWriteTokenBucket(read_rate=10.0, write_rate=5.0)
        await bucket.reconfigure(
            read_rate=300.0, write_rate=300.0,
            read_capacity=300.0, write_capacity=600.0,
        )
        assert bucket.read_rate == 300.0
        assert bucket.write_rate == 300.0
        assert bucket.read_capacity == 300.0
        assert bucket.write_capacity == 600.0

    @pytest.mark.asyncio
    async def test_reconfigure_capacity_defaults_to_rate(self) -> None:
        bucket = ReadWriteTokenBucket(read_rate=10.0, write_rate=5.0)
        await bucket.reconfigure(read_rate=50.0, write_rate=25.0)
        assert bucket.read_capacity == 50.0
        assert bucket.write_capacity == 25.0

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
            await bucket.acquire(read_cost=6.0, write_cost=0.0)
        with pytest.raises(ValueError, match="exceeds"):
            await bucket.acquire(read_cost=1.0, write_cost=4.0)

    def test_get_status(self) -> None:
        bucket = ReadWriteTokenBucket(read_rate=10.0, write_rate=5.0)
        status = bucket.get_status()
        assert status["type"] == "ReadWriteTokenBucket"
        assert status["read_tokens"] == 10.0
        assert status["write_tokens"] == 5.0


class TestConcurrentLoad:
    """Gap 1: Verify rate limiter correctness under concurrent access."""

    @pytest.mark.asyncio
    async def test_concurrent_reads_consume_correct_tokens(self) -> None:
        """5 concurrent read acquires should consume exactly 5 read tokens."""
        import asyncio

        bucket = ReadWriteTokenBucket(read_rate=10.0, write_rate=5.0)
        tasks = [bucket.acquire(read_cost=1.0, write_cost=0.0) for _ in range(5)]
        await asyncio.gather(*tasks)
        assert bucket.read_tokens == 5.0
        assert bucket.write_tokens == 5.0  # writes untouched

    @pytest.mark.asyncio
    async def test_concurrent_writes_consume_correct_tokens(self) -> None:
        """3 concurrent write acquires should consume exactly 3 write tokens."""
        import asyncio

        bucket = ReadWriteTokenBucket(read_rate=10.0, write_rate=5.0)
        tasks = [bucket.acquire(read_cost=1.0, write_cost=1.0) for _ in range(3)]
        await asyncio.gather(*tasks)
        assert bucket.write_tokens == 2.0
        assert bucket.read_tokens == 10.0  # reads untouched

    @pytest.mark.asyncio
    async def test_concurrent_mixed_load(self) -> None:
        """Mix of reads and writes under concurrent access."""
        import asyncio

        bucket = ReadWriteTokenBucket(read_rate=10.0, write_rate=5.0)
        read_tasks = [bucket.acquire(read_cost=1.0, write_cost=0.0) for _ in range(5)]
        write_tasks = [bucket.acquire(read_cost=1.0, write_cost=1.0) for _ in range(3)]
        await asyncio.gather(*read_tasks, *write_tasks)
        assert bucket.read_tokens == 5.0
        assert bucket.write_tokens == 2.0

    @pytest.mark.asyncio
    async def test_no_double_consumption(self) -> None:
        """Exhaust all tokens concurrently; verify no token is consumed twice."""
        import asyncio

        bucket = ReadWriteTokenBucket(read_rate=5.0, write_rate=5.0)
        # Try to consume 5 tokens concurrently (exactly capacity)
        results = await asyncio.gather(
            *[bucket.try_acquire(read_cost=1.0, write_cost=0.0) for _ in range(5)]
        )
        assert sum(results) == 5  # all should succeed
        assert bucket.read_tokens == 0.0

        # 6th attempt should fail (no tokens left)
        assert await bucket.try_acquire(read_cost=1.0, write_cost=0.0) is False

    @pytest.mark.asyncio
    async def test_acquire_does_not_deadlock(self) -> None:
        """Concurrent acquires that exceed capacity must not deadlock.

        Regression test: the lock must be released before sleeping so other
        coroutines can proceed when tokens refill.
        """
        import asyncio

        bucket = ReadWriteTokenBucket(read_rate=2.0, write_rate=2.0)
        # Launch 4 writes (capacity is 2), so 2 must wait for refill.
        # With a 1-second window this should complete in ~1s, not deadlock.
        results = await asyncio.wait_for(
            asyncio.gather(*[
                bucket.acquire(read_cost=0.0, write_cost=1.0) for _ in range(4)
            ]),
            timeout=5.0,
        )
        assert len(results) == 4
