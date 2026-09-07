"""Sliding-window conversation memory for multi-turn chat.

The whole history lives in the process, but only the last ``max_messages``
are replayed to the LLM, so long sessions cannot overflow the model's context
window with stale tool traffic. Storage itself is also bounded (2× window).
"""

from langchain_core.messages import BaseMessage


class ConversationMemory:
    """Bounded multi-turn chat history with a sliding replay window."""

    def __init__(self, max_messages: int = 12) -> None:
        if max_messages < 2:
            raise ValueError("max_messages must be >= 2 (human + assistant turn)")
        self.max_messages = max_messages
        self._messages: list[BaseMessage] = []

    def add_turn(self, messages: list[BaseMessage]) -> None:
        """Append one exchange (the user's message + the assistant's replies)."""
        self._messages.extend(messages)
        # Bound storage at 2× the replay window; trim on write.
        if len(self._messages) > self.max_messages * 2:
            del self._messages[: len(self._messages) - self.max_messages * 2]

    def as_list(self) -> list[BaseMessage]:
        """Copy of the messages inside the sliding window (oldest first)."""
        return list(self._messages[-self.max_messages :])

    def clear(self) -> None:
        """Forget everything (the ``clear`` REPL command)."""
        self._messages.clear()

    def __len__(self) -> int:
        return len(self._messages)


__all__ = ["ConversationMemory"]
