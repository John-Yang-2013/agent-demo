#!/usr/bin/env python3
"""
AI Agent Demo
=============
LangChain + LangGraph + Ollama  ·  model: qwen3.5

Modes:
  python main.py              # interactive chat
  python main.py --demo       # run all showcase scenarios automatically
  python main.py -q "…"       # single-shot query
"""

import argparse
import re
import sys
from typing import Optional

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from agent.config import MODEL_NAME, OLLAMA_BASE_URL
from agent.core import create_agent

console = Console()

# ---------------------------------------------------------------------------
# Demo scenarios — each showcases different tool(s)
# ---------------------------------------------------------------------------

DEMO_SCENARIOS = [
    {
        "title": "🔢  Math & Compound Interest",
        "query": (
            "I invest $15,000 at 7% annual interest for 10 years. "
            "What is the final amount using compound interest (A = P * (1 + r)^t)? "
            "Also tell me the total profit."
        ),
        "highlight": "calculator",
    },
    {
        "title": "📅  Date & Countdown",
        "query": (
            "What is today's full date, day of the week, and week number? "
            "How many days are left in this year?"
        ),
        "highlight": "get_current_datetime",
    },
    {
        "title": "🌤  Live Weather Comparison",
        "query": (
            "Compare the current weather in Tokyo and London. "
            "Which city is warmer right now, and by how many degrees Celsius?"
        ),
        "highlight": "get_weather + calculator",
    },
    {
        "title": "📚  Knowledge Lookup",
        "query": "Explain quantum entanglement in simple terms. What makes it so remarkable?",
        "highlight": "wikipedia_search",
    },
    {
        "title": "📐  Unit Conversions",
        "query": (
            "Convert 100 miles per hour to km/h and m/s. "
            "Also convert 70 kg to pounds and stones. "
            "And what is 37°C in Fahrenheit?"
        ),
        "highlight": "unit_converter",
    },
    {
        "title": "🏃  Multi-Tool Challenge",
        "query": (
            "A marathon is 42.195 km. If I run at 12 km/h, how many minutes will it take? "
            "Convert that duration to hours:minutes and also to seconds. "
            "If I burn 70 kcal per km, what is my total calorie burn?"
        ),
        "highlight": "calculator + unit_converter",
    },
    {
        "title": "🌍  Travel Planner (all tools)",
        "query": (
            "I'm flying to Sydney, Australia tomorrow. "
            "What's the current weather there? "
            "The flight is 14 hours — convert that to minutes and seconds. "
            "If my destination is 11 hours ahead of UTC, what time will it be when I land "
            "(I'm departing at 08:00 UTC today)?"
        ),
        "highlight": "get_weather + get_current_datetime + unit_converter + calculator",
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def strip_thinking(text: str) -> str:
    """Remove <think>…</think> blocks that some reasoning models emit."""
    return THINK_RE.sub("", text).strip()


def _fmt_args(args: dict) -> str:
    parts = []
    for k, v in args.items():
        parts.append(f"{k}={repr(v)}")
    joined = ", ".join(parts)
    return joined if len(joined) <= 120 else joined[:117] + "…"


def _preview(text: str, max_len: int = 180) -> str:
    text = text.replace("\n", "  ").strip()
    return text if len(text) <= max_len else text[:max_len - 1] + "…"


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

def print_banner() -> None:
    title = Text()
    title.append("  AI Agent Demo\n", style="bold bright_white")
    title.append("  LangChain · LangGraph · Ollama\n\n", style="dim white")
    title.append(f"  Model  : ", style="dim")
    title.append(f"{MODEL_NAME}\n", style="bold green")
    title.append(f"  Ollama : ", style="dim")
    title.append(f"{OLLAMA_BASE_URL}\n", style="cyan")
    title.append("  Tools  : ", style="dim")
    title.append(
        "calculator  ·  datetime  ·  weather  ·  wikipedia  ·  unit_converter",
        style="yellow",
    )
    console.print(Panel(title, border_style="bright_blue", padding=(0, 1)))
    console.print()


# ---------------------------------------------------------------------------
# Core: run one query through the agent and render output
# ---------------------------------------------------------------------------

def run_query(
    agent,
    query: str,
    recursion_limit: int = 31,
    show_panel: bool = True,
) -> Optional[str]:
    """Stream the agent, render tool calls + results, return the final answer."""

    if show_panel:
        console.print(
            Panel(
                f"[bold white]{query}[/bold white]",
                title="[cyan]You[/cyan]",
                border_style="cyan",
                padding=(0, 1),
            )
        )

    messages = [HumanMessage(content=query)]
    final_answer: Optional[str] = None
    tool_step = 0

    console.print("[dim]  ⟳ Thinking…[/dim]")
    console.print()

    try:
        for event in agent.stream(
            {"messages": messages},
            stream_mode="updates",
            config={"recursion_limit": recursion_limit},
        ):
            for _node, node_data in event.items():
                for msg in node_data.get("messages", []):

                    if isinstance(msg, AIMessage):
                        if msg.tool_calls:
                            for tc in msg.tool_calls:
                                tool_step += 1
                                console.print(
                                    f"  [bold yellow]↳ Tool #{tool_step}:[/bold yellow] "
                                    f"[yellow]{tc['name']}[/yellow]"
                                    f"([dim]{_fmt_args(tc['args'])}[/dim])"
                                )
                        else:
                            content = strip_thinking(msg.content or "")
                            if content:
                                final_answer = content

                    elif isinstance(msg, ToolMessage):
                        console.print(
                            f"    [dim green]Result ↦ {_preview(msg.content)}[/dim green]"
                        )

        console.print()

        if final_answer:
            console.print(
                Panel(
                    Markdown(final_answer),
                    title="[bold green]Agent[/bold green]",
                    border_style="green",
                    padding=(1, 2),
                )
            )
        else:
            console.print("[dim yellow]  (No text response returned)[/dim yellow]")

        return final_answer

    except Exception as exc:
        err = str(exc)
        if any(w in err.lower() for w in ("connection refused", "cannot connect", "connect")):
            console.print(
                Panel(
                    "[bold red]Cannot connect to Ollama.[/bold red]\n\n"
                    "Start the Ollama server:\n"
                    "  [cyan]ollama serve[/cyan]\n\n"
                    f"Pull the model if needed:\n"
                    f"  [cyan]ollama pull {MODEL_NAME}[/cyan]",
                    title="[red]Connection Error[/red]",
                    border_style="red",
                )
            )
        else:
            console.print(
                Panel(f"[red]{err}[/red]", title="[red]Error[/red]", border_style="red")
            )
        return None


# ---------------------------------------------------------------------------
# Demo mode
# ---------------------------------------------------------------------------

def run_demo_mode(agent, recursion_limit: int) -> None:
    console.print(
        Panel(
            f"[bold]Running [magenta]{len(DEMO_SCENARIOS)}[/magenta] showcase scenarios[/bold]\n"
            "Each scenario highlights one or more agent tools.",
            title="[bold magenta]DEMO MODE[/bold magenta]",
            border_style="magenta",
        )
    )
    console.print()

    results = []

    for idx, scenario in enumerate(DEMO_SCENARIOS, 1):
        console.print(
            Rule(
                f"[bold magenta]Scenario {idx}/{len(DEMO_SCENARIOS)} — {scenario['title']}[/bold magenta]",
                style="magenta",
            )
        )
        console.print(f"  [dim]Tools: {scenario['highlight']}[/dim]")
        console.print()

        answer = run_query(agent, scenario["query"], recursion_limit=recursion_limit)
        results.append({"title": scenario["title"], "ok": answer is not None})
        console.print()

        if idx < len(DEMO_SCENARIOS):
            try:
                console.print("[dim]  Press [bold]Enter[/bold] for next scenario…[/dim]")
                input()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Demo interrupted.[/yellow]")
                break
            console.print()

    # Summary table
    console.print(Rule("[bold green]Demo Complete[/bold green]", style="green"))
    table = Table(
        title="Results",
        box=box.ROUNDED,
        border_style="green",
        show_header=True,
        header_style="bold white",
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Scenario", style="white")
    table.add_column("Status", justify="center", width=10)

    for i, r in enumerate(results, 1):
        status = "[bold green]✓[/bold green]" if r["ok"] else "[bold red]✗[/bold red]"
        table.add_row(str(i), r["title"], status)

    console.print(table)


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------

HELP_TEXT = """\
**Example queries**

| Category | Example |
|---|---|
| Math | `What is 15% of 847, rounded to 2 decimal places?` |
| Math | `Compound interest: $5000 at 8% for 3 years` |
| DateTime | `What day of the week is today? How many days until New Year?` |
| Weather | `What's the weather in Paris right now?` |
| Weather | `Compare weather in NYC and Tokyo` |
| Knowledge | `What is the Turing test?` |
| Units | `Convert 90 mph to km/h` |
| Units | `Convert 98.6°F to Celsius and Kelvin` |
| Multi | `A 10K race at 8 min/mile — how long in minutes and seconds?` |

Type **demo** to run the showcase · **help** to see this · **quit** to exit
"""


def run_interactive_mode(agent, recursion_limit: int) -> None:
    console.print(
        Panel(
            "[bold]Interactive Chat[/bold]\n\n"
            "I have access to real-time tools — ask me to calculate, look up weather,\n"
            "search Wikipedia, convert units, or check the current date and time.\n\n"
            "Commands: [bold cyan]demo[/bold cyan]  ·  [bold cyan]help[/bold cyan]  ·  "
            "[bold red]quit[/bold red]",
            title="[bold cyan]Welcome[/bold cyan]",
            border_style="cyan",
        )
    )
    console.print()

    while True:
        try:
            user_input = console.input("[bold cyan]You ›[/bold cyan] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Bye![/yellow]")
            break

        if not user_input:
            continue

        cmd = user_input.lower()

        if cmd in ("quit", "exit", "q", "bye"):
            console.print("[yellow]Goodbye![/yellow]")
            break

        if cmd == "demo":
            run_demo_mode(agent, recursion_limit)
            continue

        if cmd == "help":
            console.print(Panel(Markdown(HELP_TEXT), border_style="yellow", title="[yellow]Help[/yellow]"))
            continue

        console.print()
        run_query(agent, user_input, recursion_limit=recursion_limit)
        console.print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Agent Demo — LangChain + LangGraph + Ollama",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py                          # interactive chat\n"
            "  python main.py --demo                   # run showcase scenarios\n"
            '  python main.py -q "Convert 5 miles to km"  # single query\n'
        ),
    )
    parser.add_argument("--demo", "-d", action="store_true", help="Run all demo scenarios")
    parser.add_argument("--query", "-q", type=str, metavar="QUERY", help="Run a single query and exit")
    args = parser.parse_args()

    print_banner()

    console.print("[dim]Initialising agent…[/dim]")
    try:
        agent, tools, recursion_limit = create_agent()
        tool_names = ", ".join(t.name for t in tools)
        console.print(f"[dim]✓ Ready — {len(tools)} tools loaded: {tool_names}[/dim]")
        console.print()
    except Exception as exc:
        console.print(f"[bold red]Failed to create agent: {exc}[/bold red]")
        sys.exit(1)

    if args.query:
        run_query(agent, args.query, recursion_limit=recursion_limit)
    elif args.demo:
        run_demo_mode(agent, recursion_limit)
    else:
        run_interactive_mode(agent, recursion_limit)


if __name__ == "__main__":
    main()
