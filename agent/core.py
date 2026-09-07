"""Agent core — creates the LangGraph ReAct agent backed by a local Ollama LLM."""

from langchain.agents import create_agent as _create_agent
from langchain_ollama import ChatOllama

from .config import config
from .tools import get_tools


def _summary_line(tool) -> str:
    """First non-empty line of a tool's description (its summary sentence)."""
    for line in (tool.description or "").strip().splitlines():
        if line.strip():
            return line.strip()
    return "(no description)"


def _build_system_prompt() -> str:
    """Build the system prompt dynamically from the registered tools."""
    tool_lines = [f"  • {t.name} — {_summary_line(t)}" for t in get_tools()]

    return f"""You are a highly capable AI assistant with access to real-time tools.
Think step-by-step and use the right tool for each part of a question.

Available tools:
{chr(10).join(tool_lines)}

Rules:
1. Always use the calculator for any numeric computation — never compute mentally.
2. Use tools proactively; chain multiple tools when a question requires it.
3. When a tool returns data, incorporate all relevant numbers in your answer.
4. Be concise but complete. Use markdown formatting where helpful.
5. If a tool call fails, explain why and suggest an alternative if possible.
6. For ANY arithmetic or unit-conversion question: first compute with
   calculator / unit_converter, then call submit_calculation with the final
   numbers, and FINALLY still write a normal text answer to the user —
   submitting alone is not enough.
"""


def create_agent():
    """Initialise the ChatOllama model and build the LangGraph ReAct agent.

    Returns:
        (agent, tools, recursion_limit) — the compiled agent graph, the list of tool objects, and recursion limit.
    """
    llm = ChatOllama(
        model=config.MODEL_NAME,
        base_url=config.OLLAMA_BASE_URL,
        temperature=config.TEMPERATURE,
        num_ctx=config.NUM_CTX,
        num_predict=config.NUM_PREDICT,
    )

    prompt = _build_system_prompt()
    tools = get_tools()
    agent = _create_agent(llm, tools, system_prompt=prompt)
    return agent, tools, config.RECURSION_LIMIT
