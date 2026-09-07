"""Tests for the TTL cache used by the weather/wikipedia tools."""

import pytest

from agent.cache import TTLCache


class FakeClock:
    """Deterministic monotonic clock — advance time without sleeping."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture()
def clock() -> FakeClock:
    return FakeClock()


def test_set_and_get_roundtrip(clock: FakeClock) -> None:
    cache = TTLCache(ttl=60, clock=clock)
    cache.set("tokyo", "sunny")
    assert cache.get("tokyo") == "sunny"
    assert cache.get("oslo") is None


def test_expired_entry_returns_none_and_is_evicted(clock: FakeClock) -> None:
    cache = TTLCache(ttl=60, clock=clock)
    cache.set("tokyo", "sunny")
    clock.advance(61)
    assert cache.get("tokyo") is None
    assert len(cache) == 0  # lazily evicted on read


def test_expiry_at_exact_ttl_boundary(clock: FakeClock) -> None:
    cache = TTLCache(ttl=60, clock=clock)
    cache.set("tokyo", "sunny")
    clock.advance(60)
    assert cache.get("tokyo") is None


def test_maxsize_evicts_oldest(clock: FakeClock) -> None:
    cache = TTLCache(ttl=60, maxsize=2, clock=clock)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_re_set_refreshes_ttl(clock: FakeClock) -> None:
    cache = TTLCache(ttl=60, clock=clock)
    cache.set("a", 1)
    clock.advance(30)
    cache.set("a", "updated")  # expiry restarts from now
    clock.advance(30)  # 60s after the first set, only 30s after the refresh
    assert cache.get("a") == "updated"


def test_get_or_set_computes_once(clock: FakeClock) -> None:
    cache = TTLCache(ttl=60, clock=clock)
    calls: list[int] = []

    def factory() -> str:
        calls.append(1)
        return "result"

    assert cache.get_or_set("k", factory) == "result"
    assert cache.get_or_set("k", factory) == "result"
    assert len(calls) == 1


def test_clear_empties_cache(clock: FakeClock) -> None:
    cache = TTLCache(ttl=60, clock=clock)
    cache.set("a", 1)
    cache.clear()
    assert cache.get("a") is None
    assert len(cache) == 0


@pytest.mark.parametrize("kwargs", [{"ttl": 0}, {"ttl": -5}, {"ttl": 60, "maxsize": 0}])
def test_invalid_args_raise(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        TTLCache(**kwargs)
