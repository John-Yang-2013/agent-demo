"""A tiny thread-safe in-memory TTL cache used to memoize tool results.

Deliberately dependency-free (no cachetools/redis): the demo only needs
per-process expiry, and an injectable clock keeps the logic trivially testable.
"""

import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any


class TTLCache:
    """In-memory key→value cache where entries expire after ``ttl`` seconds.

    - ``maxsize`` bounds memory: oldest entries are evicted first (FIFO).
    - ``clock`` is injectable, so tests can time-travel without sleeping.
    - ``None`` means "no cached value"; never cache ``None`` results.
    """

    def __init__(
        self,
        ttl: float,
        maxsize: int = 128,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if ttl <= 0:
            raise ValueError(f"ttl must be positive, got {ttl}")
        if maxsize <= 0:
            raise ValueError(f"maxsize must be positive, got {maxsize}")
        self._ttl = ttl
        self._maxsize = maxsize
        self._clock = clock
        self._data: OrderedDict[Any, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: Any) -> Any | None:
        """Return the cached value for ``key``, or None if absent/expired."""
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at <= self._clock():
                del self._data[key]  # lazy eviction on read
                return None
            return value

    def set(self, key: Any, value: Any) -> None:
        """Store ``value`` under ``key``, evicting the oldest entry if full."""
        with self._lock:
            self._data[key] = (self._clock() + self._ttl, value)
            self._data.move_to_end(key)
            while len(self._data) > self._maxsize:
                self._data.popitem(last=False)

    def get_or_set(self, key: Any, factory: Callable[[], Any]) -> Any:
        """Return the cached value, computing it via ``factory`` on a miss."""
        value = self.get(key)
        if value is None:
            value = factory()
            self.set(key, value)
        return value

    def clear(self) -> None:
        """Drop everything."""
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        return len(self._data)


__all__ = ["TTLCache"]
