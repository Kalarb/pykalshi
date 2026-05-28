"""Disjoint read/write token bucket rate limiter.

A request consumes EITHER read tokens OR write tokens, never both.
This matches Kalshi's actual rate limit model where read and write
limits are independently enforced.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Tuple


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

        self._read_history: deque[Tuple[float, float]] = deque()
        self._write_history: deque[Tuple[float, float]] = deque()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        expiry_threshold = now - self.window_size

        while self._read_history:
            timestamp, cost = self._read_history[0]
            if timestamp <= expiry_threshold:
                self._read_history.popleft()
                self.read_tokens = min(self.read_capacity, self.read_tokens + cost)
            else:
                break

        while self._write_history:
            timestamp, cost = self._write_history[0]
            if timestamp <= expiry_threshold:
                self._write_history.popleft()
                self.write_tokens = min(self.write_capacity, self.write_tokens + cost)
            else:
                break

    def _can_proceed(self, global_cost: float, write_cost: float) -> bool:
        if write_cost > 0:
            return self.write_tokens >= write_cost
        return self.read_tokens >= global_cost

    def _calculate_wait_time(self, global_cost: float, write_cost: float) -> float:
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
            if self.read_tokens >= global_cost:
                return 0.0
            needed = global_cost - self.read_tokens
            recovered = 0.0
            for timestamp, amount in self._read_history:
                recovered += amount
                if recovered >= needed:
                    target_time = timestamp + self.window_size + self.safety_padding
                    return max(0.0, target_time - now)
            return 1.0

    def _consume(self, global_cost: float, write_cost: float) -> None:
        now = time.monotonic()
        if write_cost > 0:
            self.write_tokens -= write_cost
            self._write_history.append((now, write_cost))
        else:
            self.read_tokens -= global_cost
            self._read_history.append((now, global_cost))

    async def acquire(self, global_cost: float = 1.0, write_cost: float = 0.0) -> None:
        """Acquire tokens, blocking until available."""
        if write_cost > 0 and write_cost > self.write_capacity:
            raise ValueError(f"Write cost {write_cost} exceeds write capacity")
        if write_cost == 0 and global_cost > self.read_capacity:
            raise ValueError(f"Read cost {global_cost} exceeds read capacity")

        async with self._lock:
            while True:
                self._refill()
                if self._can_proceed(global_cost, write_cost):
                    self._consume(global_cost, write_cost)
                    return
                wait_time = self._calculate_wait_time(global_cost, write_cost)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                else:
                    await asyncio.sleep(0.01)

    async def try_acquire(
        self, global_cost: float = 1.0, write_cost: float = 0.0
    ) -> bool:
        """Try to acquire tokens without blocking. Returns True if acquired."""
        if write_cost > 0 and write_cost > self.write_capacity:
            return False
        if write_cost == 0 and global_cost > self.read_capacity:
            return False

        async with self._lock:
            self._refill()
            if self._can_proceed(global_cost, write_cost):
                self._consume(global_cost, write_cost)
                return True
            return False

    async def get_wait_time(
        self, global_cost: float = 1.0, write_cost: float = 0.0
    ) -> float:
        """Estimate wait time without consuming tokens."""
        async with self._lock:
            self._refill()
            if self._can_proceed(global_cost, write_cost):
                return 0.0
            return self._calculate_wait_time(global_cost, write_cost)

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
        async with self._lock:
            self.read_rate = read_rate
            self.write_rate = write_rate
            self.read_capacity = read_capacity if read_capacity is not None else read_rate
            self.write_capacity = write_capacity if write_capacity is not None else write_rate
            self.read_tokens = min(self.read_tokens, self.read_capacity)
            self.write_tokens = min(self.write_tokens, self.write_capacity)

    def get_status(self) -> dict[str, object]:
        """Return current token bucket state for debugging."""
        return {
            "type": "ReadWriteTokenBucket",
            "read_tokens": self.read_tokens,
            "write_tokens": self.write_tokens,
            "read_history_len": len(self._read_history),
            "write_history_len": len(self._write_history),
        }
