"""Agent execution orchestration.

This module wires the compiled LangGraph agent to the UI layer: it streams the
agent, dispatches render calls for tool invocations / results, and drives the
three run modes (single query, demo showcase, interactive REPL).

Keeping this separate from `ui.py` means the presentation primitives are pure
and the orchestration logic can be tested / replaced independently.
"""

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from . import ui
from .scenarios import DEMO_SCENARIOS

# Connection-related substrings that indicate the Ollama server is unreachable.
_CONNECTION_HINTS = ("connection refused", "cannot connect", "connect")


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
) -> str | None:
    """Stream the agent, render tool calls + results, return the final answer."""
    if show_panel:
        ui.render_user_query(query)

    messages = [HumanMessage(content=query)]
    final_answer: str | None = None
    tool_step = 0

    ui.render_thinking()

    try:
        for event in agent.stream(
            {"messages": messages},
            stream_mode="updates",
            config={"recursion_limit": recursion_limit},
        ):
            # event.items() yields (node_name, {"messages": [Message1, ...]})
            # we only care about the messages, not the node names.
            messages_container: dict = next(iter(event.values()), {})
            for msg in messages_container.get("messages", []):
                if isinstance(msg, AIMessage):
                    if msg.tool_calls:
                        for tc in msg.tool_calls:
                            tool_step += 1
                            ui.render_tool_call(tool_step, tc["name"], tc["args"])
                    else:
                        content = ui.strip_thinking(_content_str(msg.content))
                        if content:
                            final_answer = content
                elif isinstance(msg, ToolMessage):
                    ui.render_tool_result(_content_str(msg.content))

        ui.render_blank()

        if final_answer:
            ui.render_final_answer(final_answer)
        else:
            ui.render_no_answer()

        return final_answer

    except Exception as exc:
        err = str(exc)
        if any(hint in err.lower() for hint in _CONNECTION_HINTS):
            ui.render_connection_error()
        else:
            ui.render_error(err)
        return None


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
    """REPL: read user input, dispatch commands, run queries until quit."""
    ui.render_welcome()

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

        ui.render_blank()
        run_query(agent, user_input, recursion_limit=recursion_limit)
        ui.render_blank()


__all__ = ["run_query", "run_demo_mode", "run_interactive_mode"]
