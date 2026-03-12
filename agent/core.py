"""Agent core — creates the LangGraph ReAct agent backed by a local Ollama LLM."""

from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

from .config import OLLAMA_BASE_URL, MODEL_NAME, TEMPERATURE, RECURSION_LIMIT
from .tools import TOOLS

SYSTEM_PROMPT = """\
You are a highly capable AI assistant with access to real-time tools.
Think step-by-step and use the right tool for each part of a question.

Available tools:
  • calculator         — safe arithmetic and math functions (sqrt, sin, log, etc.)
  • get_current_datetime — current date/time in any timezone; day-of-week, week number
  • get_weather        — live weather for any city or location worldwide
  • wikipedia_search   — factual knowledge: science, history, people, places, concepts
  • unit_converter     — convert between length, mass, speed, temperature, data, time…

Rules:
1. Always use the calculator for any numeric computation — never compute mentally.
2. Use tools proactively; chain multiple tools when a question requires it.
3. When a tool returns data, incorporate all relevant numbers in your answer.
4. Be concise but complete. Use markdown formatting where helpful.
5. If a tool call fails, explain why and suggest an alternative if possible.
"""


def create_agent():
    """Initialise the ChatOllama model and build the LangGraph ReAct agent.

    Returns:
        (agent, tools) — the compiled agent graph and the list of tool objects.
    """
    llm = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_BASE_URL,
        temperature=TEMPERATURE,
        num_predict=4096,
    )

    agent = create_react_agent(llm, TOOLS, prompt=SYSTEM_PROMPT)
    return agent, TOOLS, RECURSION_LIMIT
