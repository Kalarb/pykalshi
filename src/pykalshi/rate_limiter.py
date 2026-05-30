"""Disjoint read/write token bucket rate limiter.

A request consumes EITHER read tokens OR write tokens, never both.
This matches Kalshi's actual rate limit model where read and write
limits are independently enforced.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque


class ReadWriteTokenBucket:
    """Sliding-window token bucket with separate read and write budgets."""

    def __init__(self, read_rate: float, write_rate: float) -> None:
        if read_rate <= 0 or write_rate <= 0:
            raise ValueError("Rates must be positive")

        self.read_rate = read_rate
        self.write_rate = write_rate
        self.read_capacity = read_rate
        self.write_capacity = write_rate
        self.window_size = 1.0
        self.safety_padding = 0.1

        self.read_tokens = float(self.read_capacity)
        self.write_tokens = float(self.write_capacity)

        self._read_history: deque[tuple[float, float]] = deque()
        self._write_history: deque[tuple[float, float]] = deque()
        self._read_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()

    def _refill_read(self) -> None:
        expiry = time.monotonic() - self.window_size
        while self._read_history:
            ts, cost = self._read_history[0]
            if ts <= expiry:
                self._read_history.popleft()
                self.read_tokens = min(self.read_capacity, self.read_tokens + cost)
            else:
                break

    def _refill_write(self) -> None:
        expiry = time.monotonic() - self.window_size
        while self._write_history:
            ts, cost = self._write_history[0]
            if ts <= expiry:
                self._write_history.popleft()
                self.write_tokens = min(self.write_capacity, self.write_tokens + cost)
            else:
                break

    def _can_proceed(self, read_cost: float, write_cost: float) -> bool:
        if write_cost > 0:
            return self.write_tokens >= write_cost
        return self.read_tokens >= read_cost

    def _calculate_wait_time(self, read_cost: float, write_cost: float) -> float:
        now = time.monotonic()

        if write_cost > 0:
            if self.write_tokens >= write_cost:
                return 0.0
            needed = write_cost - self.write_tokens
            recovered = 0.0
            for timestamp, amount in self._write_history:
                recovered += amount
                if recovered >= needed:
                    target_time = timestamp + self.window_size + self.safety_padding
                    return max(0.0, target_time - now)
            return 1.0
        else:
            if self.read_tokens >= read_cost:
                return 0.0
            needed = read_cost - self.read_tokens
            recovered = 0.0
            for timestamp, amount in self._read_history:
                recovered += amount
                if recovered >= needed:
                    target_time = timestamp + self.window_size + self.safety_padding
                    return max(0.0, target_time - now)
            return 1.0

    def _consume(self, read_cost: float, write_cost: float) -> None:
        now = time.monotonic()
        if write_cost > 0:
            self.write_tokens -= write_cost
            self._write_history.append((now, write_cost))
        else:
            self.read_tokens -= read_cost
            self._read_history.append((now, read_cost))

    async def acquire(self, read_cost: float = 10.0, write_cost: float = 0.0) -> None:
        """Acquire tokens, blocking until available."""
        if write_cost > 0 and write_cost > self.write_capacity:
            raise ValueError(f"Write cost {write_cost} exceeds write capacity")
        if write_cost == 0 and read_cost > self.read_capacity:
            raise ValueError(f"Read cost {read_cost} exceeds read capacity")

        lock = self._write_lock if write_cost > 0 else self._read_lock
        while True:
            async with lock:
                if write_cost > 0:
                    self._refill_write()
                else:
                    self._refill_read()
                if self._can_proceed(read_cost, write_cost):
                    self._consume(read_cost, write_cost)
                    return
                wait_time = self._calculate_wait_time(read_cost, write_cost)
            # Sleep OUTSIDE the lock to avoid deadlock
            await asyncio.sleep(max(wait_time, 0.01))

    async def try_acquire(
        self, read_cost: float = 10.0, write_cost: float = 0.0
    ) -> bool:
        """Try to acquire tokens without blocking. Returns True if acquired."""
        if write_cost > 0 and write_cost > self.write_capacity:
            return False
        if write_cost == 0 and read_cost > self.read_capacity:
            return False

        lock = self._write_lock if write_cost > 0 else self._read_lock
        async with lock:
            if write_cost > 0:
                self._refill_write()
            else:
                self._refill_read()
            if self._can_proceed(read_cost, write_cost):
                self._consume(read_cost, write_cost)
                return True
            return False

    async def get_wait_time(
        self, read_cost: float = 10.0, write_cost: float = 0.0
    ) -> float:
        """Estimate wait time without consuming tokens."""
        lock = self._write_lock if write_cost > 0 else self._read_lock
        async with lock:
            if write_cost > 0:
                self._refill_write()
            else:
                self._refill_read()
            if self._can_proceed(read_cost, write_cost):
                return 0.0
            return self._calculate_wait_time(read_cost, write_cost)

    async def reconfigure(
        self,
        read_rate: float,
        write_rate: float,
        read_capacity: float | None = None,
        write_capacity: float | None = None,
    ) -> None:
        """Update rate limits (e.g., after fetching from API).

        Capacity defaults to rate when not provided (one second of budget).
        Kalshi's write bucket on higher tiers has capacity > rate for burst.
        """
        if read_rate <= 0 or write_rate <= 0:
            raise ValueError("Rates must be positive")
        async with self._read_lock:
            async with self._write_lock:
                self.read_rate = read_rate
                self.write_rate = write_rate
                self.read_capacity = read_capacity if read_capacity is not None else read_rate
                self.write_capacity = write_capacity if write_capacity is not None else write_rate
                self.read_tokens = float(self.read_capacity)
                self.write_tokens = float(self.write_capacity)
                self._read_history.clear()
                self._write_history.clear()

    def get_status(self) -> dict[str, object]:
        """Return current token bucket state for debugging."""
        return {
            "type": "ReadWriteTokenBucket",
            "read_tokens": self.read_tokens,
            "write_tokens": self.write_tokens,
            "read_history_len": len(self._read_history),
            "write_history_len": len(self._write_history),
        }
