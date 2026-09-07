"""Integration-style tests: run_query with a fake agent graph + conversation memory."""

from collections.abc import Iterator
from typing import Any

from langchain_core.messages import AIMessage

from agent import runner
from agent.memory import ConversationMemory


class FakeAgent:
    """Mimics the compiled LangGraph agent's .stream(stream_mode='updates')."""

    def __init__(self, answer: str = "ok") -> None:
        self.answer = answer
        self.inputs: list[dict] = []

    def stream(
        self, payload: dict, stream_mode: str | None = None, config: dict | None = None
    ) -> Iterator[dict[str, dict[str, list[Any]]]]:
        self.inputs.append(payload)
        yield ("updates", {"agent": {"messages": [AIMessage(content=self.answer)]}})


def test_run_query_appends_turn_to_memory() -> None:
    fake = FakeAgent(answer="the answer")
    memory = ConversationMemory(max_messages=8)

    result = runner.run_query(fake, "hi", show_panel=False, memory=memory)

    assert result == "the answer"
    assert [type(m).__name__ for m in memory.as_list()] == ["HumanMessage", "AIMessage"]


def test_run_query_replays_history_on_next_turn() -> None:
    fake = FakeAgent()
    memory = ConversationMemory(max_messages=8)

    runner.run_query(fake, "first", show_panel=False, memory=memory)
    runner.run_query(fake, "second", show_panel=False, memory=memory)

    second_input = fake.inputs[1]["messages"]
    assert [type(m).__name__ for m in second_input] == [
        "HumanMessage",
        "AIMessage",
        "HumanMessage",
    ]
    assert second_input[-1].content == "second"


def test_run_query_without_memory_is_stateless() -> None:
    fake = FakeAgent()
    runner.run_query(fake, "only", show_panel=False)
    assert len(fake.inputs[0]["messages"]) == 1


def test_run_query_does_not_save_partial_turn_on_error() -> None:
    class ExplodingAgent:
        def stream(
            self, payload: dict, stream_mode: str | None = None, config: dict | None = None
        ) -> Iterator[dict[str, dict[str, list[Any]]]]:
            yield ("updates", {"agent": {"messages": [AIMessage(content="partial")]}})
            raise RuntimeError("boom")

    memory = ConversationMemory()
    result = runner.run_query(ExplodingAgent(), "q", show_panel=False, memory=memory)

    assert result is None
    assert len(memory) == 0  # partial turn discarded
