"""Tests for the sliding-window conversation memory."""

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.memory import ConversationMemory


def _turn(n: int) -> list:
    return [HumanMessage(content=f"q{n}"), AIMessage(content=f"a{n}")]


def test_add_turn_and_as_list_roundtrip() -> None:
    memory = ConversationMemory(max_messages=4)
    memory.add_turn(_turn(1))
    memory.add_turn(_turn(2))
    assert [m.content for m in memory.as_list()] == ["q1", "a1", "q2", "a2"]
    assert len(memory) == 4


def test_window_keeps_only_most_recent_messages() -> None:
    memory = ConversationMemory(max_messages=4)
    for n in range(1, 5):
        memory.add_turn(_turn(n))
    assert [m.content for m in memory.as_list()] == ["q3", "a3", "q4", "a4"]


def test_storage_bounded_at_double_window() -> None:
    memory = ConversationMemory(max_messages=4)
    for n in range(1, 20):
        memory.add_turn(_turn(n))
    assert len(memory) == 8  # 2 × window
    assert [m.content for m in memory.as_list()] == ["q18", "a18", "q19", "a19"]


def test_tool_messages_kept_within_turn() -> None:
    memory = ConversationMemory(max_messages=6)
    memory.add_turn(
        [
            HumanMessage(content="weather?"),
            AIMessage(content=""),
            ToolMessage(content="sunny", tool_call_id="1"),
            AIMessage(content="it is sunny"),
        ]
    )
    assert len(memory.as_list()) == 4


def test_clear_resets_history() -> None:
    memory = ConversationMemory()
    memory.add_turn(_turn(1))
    memory.clear()
    assert len(memory) == 0
    assert memory.as_list() == []


def test_invalid_max_messages_raises() -> None:
    with pytest.raises(ValueError):
        ConversationMemory(max_messages=1)
