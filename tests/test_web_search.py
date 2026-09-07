"""Tests for the web_search tool (ddgs-backed, cached, failure-safe)."""

from agent import tools


def _fake_rows() -> list[dict]:
    return [
        {
            "title": "LangGraph overview",
            "href": "https://docs.langchain.com/langgraph",
            "body": "The orchestration runtime for durable agents.",
        },
        {
            "title": "Real Python tutorial",
            "href": "https://realpython.com/langgraph-python/",
            "body": "Build stateful AI agents in Python.",
        },
    ]


def test_formats_results(monkeypatch) -> None:
    calls: list[tuple[str, int]] = []

    def fake(query: str, max_results: int) -> list[dict]:
        calls.append((query, max_results))
        return _fake_rows()

    tools._SEARCH_CACHE.clear()
    monkeypatch.setattr(tools, "_ddgs_text", fake)
    out = tools.web_search.invoke({"query": "langgraph"})
    assert "1. LangGraph overview" in out
    assert "https://docs.langchain.com/langgraph" in out
    assert "The orchestration runtime" in out
    assert "2. Real Python tutorial" in out
    assert calls == [("langgraph", 5)]


def test_second_call_served_from_cache(monkeypatch) -> None:
    calls: list[str] = []

    def fake(query: str, max_results: int) -> list[dict]:
        calls.append(query)
        return _fake_rows()

    tools._SEARCH_CACHE.clear()
    monkeypatch.setattr(tools, "_ddgs_text", fake)
    tools.web_search.invoke({"query": "cache me"})
    tools.web_search.invoke({"query": "  CACHE   ME "})  # normalized to same key
    assert len(calls) == 1


def test_max_results_clamped(monkeypatch) -> None:
    calls: list[int] = []

    def fake(query: str, max_results: int) -> list[dict]:
        calls.append(max_results)
        return _fake_rows()

    tools._SEARCH_CACHE.clear()
    monkeypatch.setattr(tools, "_ddgs_text", fake)
    tools.web_search.invoke({"query": "clamp high", "max_results": 99})
    tools.web_search.invoke({"query": "clamp low", "max_results": 0})
    assert calls == [8, 1]


def test_no_results_message(monkeypatch) -> None:
    tools._SEARCH_CACHE.clear()
    monkeypatch.setattr(tools, "_ddgs_text", lambda q, m: [])
    out = tools.web_search.invoke({"query": "nothing matches this"})
    assert "No results found" in out


def test_error_returns_message_and_is_not_cached(monkeypatch) -> None:
    def boom(query: str, max_results: int) -> list[dict]:
        raise RuntimeError("network down")

    tools._SEARCH_CACHE.clear()
    monkeypatch.setattr(tools, "_ddgs_text", boom)
    out = tools.web_search.invoke({"query": "will fail"})
    assert "Web search failed" in out
    assert "network down" in out

    # A later success for the same key must not be poisoned by the failure.
    monkeypatch.setattr(tools, "_ddgs_text", lambda q, m: _fake_rows())
    out2 = tools.web_search.invoke({"query": "will fail"})
    assert "LangGraph overview" in out2
