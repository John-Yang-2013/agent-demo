"""run_query with dual-mode streaming events + transient-error retry."""

from collections.abc import Iterator
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk

from agent import runner
from agent.memory import ConversationMemory


def _msg_event(text: str, node: str = "model") -> tuple[str, Any]:
    return ("messages", (AIMessageChunk(content=text), {"langgraph_node": node}))


def _upd_event(answer: str) -> tuple[str, dict[str, dict[str, list[Any]]]]:
    return ("updates", {"agent": {"messages": [AIMessage(content=answer)]}})


class FakeAgent:
    """Mimics the agent's dual-mode stream (["updates", "messages"])."""

    def __init__(self, script: list[list[tuple[str, Any]]] | None = None) -> None:
        self.script = script or [[_msg_event("Hel"), _msg_event("lo"), _upd_event("Hello")]]
        self.calls = 0
        self.inputs: list[dict] = []

    def stream(
        self, payload: dict, stream_mode: str | None = None, config: dict | None = None
    ) -> Iterator[tuple[str, Any]]:
        self.calls += 1
        self.inputs.append(payload)
        yield from self.script[(self.calls - 1) % len(self.script)]


def test_streaming_events_yield_final_answer() -> None:
    fake = FakeAgent()
    assert runner.run_query(fake, "q", show_panel=False) == "Hello"


def test_tool_node_chunks_are_not_streamed() -> None:
    fake = FakeAgent(
        script=[
            [
                _msg_event("6 * 7 = 42", node="tools"),  # tool result echo
                _msg_event("4"),
                _msg_event("2"),
                _upd_event("42"),
            ]
        ]
    )
    assert runner.run_query(fake, "q", show_panel=False) == "42"


def test_memory_still_recorded_with_streaming() -> None:
    fake = FakeAgent()
    memory = ConversationMemory()
    runner.run_query(fake, "q", show_panel=False, memory=memory)
    assert [type(m).__name__ for m in memory.as_list()] == ["HumanMessage", "AIMessage"]


def test_transient_error_retried_then_succeeds(monkeypatch) -> None:
    monkeypatch.setattr(runner, "_sleep", lambda s: None)

    class FlakyAgent:
        def __init__(self) -> None:
            self.calls = 0

        def stream(self, payload, stream_mode=None, config=None) -> Iterator[tuple[str, Any]]:
            self.calls += 1
            if self.calls == 1:
                raise ConnectionError("connection refused")
            yield _upd_event("recovered")

    fake = FlakyAgent()
    assert runner.run_query(fake, "q", show_panel=False) == "recovered"
    assert fake.calls == 2


def test_non_transient_error_fails_fast() -> None:
    class BoomAgent:
        def __init__(self) -> None:
            self.calls = 0

        def stream(self, payload, stream_mode=None, config=None) -> Iterator[tuple[str, Any]]:
            self.calls += 1
            raise RuntimeError("boom")

    fake = BoomAgent()
    assert runner.run_query(fake, "q", show_panel=False) is None
    assert fake.calls == 1  # no retry for non-transient errors


def test_retries_exhausted_with_backoff(monkeypatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(runner, "_sleep", sleeps.append)

    class AlwaysDown:
        def __init__(self) -> None:
            self.calls = 0

        def stream(self, payload, stream_mode=None, config=None) -> Iterator[tuple[str, Any]]:
            self.calls += 1
            raise ConnectionError("connection refused by server")

    fake = AlwaysDown()
    assert runner.run_query(fake, "q", show_panel=False) is None
    assert fake.calls == 3  # 1 initial + 2 retries
    assert sleeps == [1.0, 2.0]  # exponential backoff


def test_is_transient_heuristics() -> None:
    assert runner._is_transient(ConnectionError("x")) is True
    assert runner._is_transient(TimeoutError("x")) is True
    assert runner._is_transient(RuntimeError("connect call failed")) is True
    assert runner._is_transient(ValueError("bad arg")) is False
    assert runner._is_transient(RuntimeError("boom")) is False
