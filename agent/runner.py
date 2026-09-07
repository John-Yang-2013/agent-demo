"""Agent execution orchestration.

This module wires the compiled LangGraph agent to the UI layer: it streams the
agent, dispatches render calls for tool invocations / results, and drives the
three run modes (single query, demo showcase, interactive REPL).

Keeping this separate from `ui.py` means the presentation primitives are pure
and the orchestration logic can be tested / replaced independently.
"""

import time
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage

from . import ui
from .config import config
from .memory import ConversationMemory
from .scenarios import DEMO_SCENARIOS

# Connection-related substrings that indicate the Ollama server is unreachable.
_CONNECTION_HINTS = ("connection refused", "cannot connect", "connect")

# Transient failures are retried with exponential backoff; everything else
# fails fast. `_sleep` is injectable so tests never actually wait.
_sleep = time.sleep

_TRANSIENT_EXC_TYPES = (ConnectionError, TimeoutError, OSError)
_TRANSIENT_HINTS = (
    "connect",
    "connection",
    "timeout",
    "timed out",
    "refused",
    "reset",
    "unreachable",
    "broken pipe",
)


def _is_transient(exc: Exception) -> bool:
    """Best-effort check whether an error is a transient network hiccup."""
    if isinstance(exc, _TRANSIENT_EXC_TYPES):
        return True
    msg = str(exc).lower()
    return any(hint in msg for hint in _TRANSIENT_HINTS)


def _content_str(content: str | list[str | dict[str, Any]] | None) -> str:
    """Coerce a LangChain message's `content` (str or list of content blocks) to text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    # Multimodal / structured content blocks: extract text parts.
    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict):
            text = block.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "".join(parts)


# --------------------------------------------------------------------------- #
# Core: run one query through the agent and render output
# --------------------------------------------------------------------------- #


def run_query(
    agent,
    query: str,
    recursion_limit: int = 31,
    show_panel: bool = True,
    memory: ConversationMemory | None = None,
) -> str | None:
    """Stream the agent, render tool calls + results, return the final answer.

    When ``memory`` is given the dialogue is multi-turn: prior history is
    replayed to the agent and the finished exchange (user message + agent
    replies and tool traffic) is appended to the memory afterwards. Without
    it the call stays stateless, exactly as before.

    Answers are streamed token-by-token when ``STREAM_TOKENS`` is on, and
    transient network failures are retried with exponential backoff
    (``LLM_RETRIES`` / ``LLM_RETRY_DELAY``).
    """
    if show_panel:
        ui.render_user_query(query)

    history = memory.as_list() if memory is not None else []
    messages = [*history, HumanMessage(content=query)]

    max_attempts = config.LLM_RETRIES + 1
    delay = config.LLM_RETRY_DELAY

    for attempt in range(1, max_attempts + 1):
        new_turn: list[Any] = [HumanMessage(content=query)]
        final_answer: str | None = None
        tool_step = 0
        live = ui.LiveTokenStream() if (config.STREAM_TOKENS and show_panel) else None

        ui.render_thinking()

        try:
            for mode, data in agent.stream(
                {"messages": messages},
                stream_mode=["updates", "messages"],
                config={"recursion_limit": recursion_limit},
            ):
                if mode == "messages":
                    # (message_chunk, metadata) — stream final-answer tokens
                    # live. Only chunks from the model node carry answer text;
                    # tool-node messages are rendered via "updates" below.
                    chunk, meta = data
                    if (
                        live is not None
                        and meta.get("langgraph_node") == "model"
                        and isinstance(chunk, AIMessageChunk)
                    ):
                        text = _content_str(chunk.content)
                        if text:
                            live.feed(text)
                    continue

                # "updates" — data is {node_name: {"messages": [Message1, …]}};
                # we only care about the messages, not the node names.
                node_updates: dict = data if isinstance(data, dict) else {}
                messages_container: dict = next(iter(node_updates.values()), {})
                for msg in messages_container.get("messages", []):
                    new_turn.append(msg)
                    if isinstance(msg, AIMessage):
                        if msg.tool_calls:
                            if live is not None:
                                live.end_segment()  # narration ends, tool panel follows
                            for tc in msg.tool_calls:
                                tool_step += 1
                                ui.render_tool_call(tool_step, tc["name"], tc["args"])
                        else:
                            content = ui.strip_thinking(_content_str(msg.content))
                            if content:
                                final_answer = content
                    elif isinstance(msg, ToolMessage):
                        ui.render_tool_result(_content_str(msg.content))

            if live is not None:
                live.finish()

            ui.render_blank()

            if final_answer:
                if live is None or not live.segment_printed:
                    ui.render_final_answer(final_answer)
                # else: the answer was already rendered live, token by token
            else:
                ui.render_no_answer()

            if memory is not None:
                memory.add_turn(new_turn)

            return final_answer

        except Exception as exc:
            if live is not None:
                live.finish()  # close a half-printed line before error output
            if _is_transient(exc) and attempt < max_attempts:
                ui.render_retry(attempt, max_attempts, delay)
                _sleep(delay)
                delay *= 2
                continue
            err = str(exc)
            if any(hint in err.lower() for hint in _CONNECTION_HINTS):
                ui.render_connection_error()
            else:
                ui.render_error(err)
            return None

    return None  # unreachable: the last attempt always returns above


# --------------------------------------------------------------------------- #
# Demo mode
# --------------------------------------------------------------------------- #


def run_demo_mode(agent, recursion_limit: int) -> None:
    """Run every showcase scenario in turn, rendering a summary table at the end."""
    ui.render_demo_header(len(DEMO_SCENARIOS))

    results: list[dict] = []

    for idx, scenario in enumerate(DEMO_SCENARIOS, 1):
        is_last = idx == len(DEMO_SCENARIOS)
        ui.render_scenario_rule(idx, len(DEMO_SCENARIOS), scenario["title"], scenario["highlight"])

        answer = run_query(agent, scenario["query"], recursion_limit=recursion_limit)
        results.append({"title": scenario["title"], "ok": answer is not None})
        ui.render_blank()

        if not ui.render_scenario_pause(is_last):
            break

        ui.render_blank()

    ui.render_demo_complete()
    ui.render_demo_results_table(results)


# --------------------------------------------------------------------------- #
# Interactive mode
# --------------------------------------------------------------------------- #


def run_interactive_mode(agent, recursion_limit: int) -> None:
    """Multi-turn REPL: keeps conversation memory until the user quits or clears."""
    ui.render_welcome()
    memory = ConversationMemory(config.HISTORY_MAX_MESSAGES)

    while True:
        try:
            user_input = ui.prompt_user()
        except (KeyboardInterrupt, EOFError):
            ui.render_interrupted()
            break

        if not user_input:
            continue

        cmd = user_input.lower()

        if cmd in ("quit", "exit", "q", "bye"):
            ui.render_goodbye()
            break

        if cmd == "demo":
            run_demo_mode(agent, recursion_limit)
            continue

        if cmd == "help":
            ui.render_help()
            continue

        if cmd == "clear":
            memory.clear()
            ui.render_memory_cleared()
            continue

        ui.render_blank()
        run_query(agent, user_input, recursion_limit=recursion_limit, memory=memory)
        ui.render_blank()


__all__ = ["run_query", "run_demo_mode", "run_interactive_mode"]
