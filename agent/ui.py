"""Rich terminal UI rendering primitives.

All visual output (panels, tables, tool-call traces, error boxes) lives here so
that the orchestration layer (`runner.py`) stays free of presentation concerns
and is easy to test / replace (e.g. swapping Rich for a web frontend later).
"""

import re

from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from .config import config
from .scenarios import DEMO_SCENARIOS, HELP_TEXT
from .tools import get_tools

# A single shared console for the whole CLI.
console = Console()

# Some reasoning models (e.g. qwen3) wrap internal monologue in <think>…</think>.
THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


# --------------------------------------------------------------------------- #
# Text helpers
# --------------------------------------------------------------------------- #


def strip_thinking(text: str) -> str:
    """Remove <think>…</think> blocks that some reasoning models emit."""
    return THINK_RE.sub("", text).strip()


def fmt_args(args: dict) -> str:
    """Format a tool-call args dict into a compact single-line string."""
    parts = [f"{k}={v!r}" for k, v in args.items()]
    joined = ", ".join(parts)
    return joined if len(joined) <= 120 else joined[:117] + "…"


def preview(text: str | None, max_len: int = 180) -> str:
    """Collapse a (possibly multi-line) string into a short single-line preview."""
    text = (text or "").replace("\n", "  ").strip()
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


# --------------------------------------------------------------------------- #
# Startup / status
# --------------------------------------------------------------------------- #


def print_banner() -> None:
    title = Text()
    title.append("  AI Agent Demo\n", style="bold bright_white")
    title.append("  LangChain · LangGraph · Ollama\n\n", style="dim white")
    title.append("  Model  : ", style="dim")
    title.append(f"{config.MODEL_NAME}\n", style="bold green")
    title.append("  Ollama : ", style="dim")
    title.append(f"{config.OLLAMA_BASE_URL}\n", style="cyan")
    title.append("  Tools  : ", style="dim")
    title.append("  ·  ".join(t.name for t in get_tools()), style="yellow")
    console.print(Panel(title, border_style="bright_blue", padding=(0, 1)))
    console.print()


def render_initialising() -> None:
    console.print("[dim]Initialising agent…[/dim]")


def render_ready(tools: list) -> None:
    tool_names = ", ".join(t.name for t in tools)
    console.print(f"[dim]✓ Ready — {len(tools)} tools loaded: {tool_names}[/dim]")
    console.print()


def render_init_error(exc: Exception) -> None:
    console.print(f"[bold red]Failed to create agent: {exc}[/bold red]")


# --------------------------------------------------------------------------- #
# Query rendering
# --------------------------------------------------------------------------- #


def render_user_query(query: str) -> None:
    console.print(
        Panel(
            f"[bold white]{query}[/bold white]",
            title="[cyan]You[/cyan]",
            border_style="cyan",
            padding=(0, 1),
        )
    )


def render_thinking() -> None:
    console.print("[dim]  ⟳ Thinking…[/dim]")
    console.print()


def render_tool_call(step: int, name: str, args: dict) -> None:
    console.print(
        f"  [bold yellow]↳ Tool #{step}:[/bold yellow] "
        f"[yellow]{name}[/yellow]"
        f"([dim]{fmt_args(args)}[/dim])"
    )


def render_tool_result(content: str) -> None:
    console.print(f"    [dim green]Result ↦ {preview(content)}[/dim green]")


def render_final_answer(answer: str) -> None:
    console.print(
        Panel(
            Markdown(answer),
            title="[bold green]Agent[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )


def render_no_answer() -> None:
    console.print("[dim yellow]  (No text response returned)[/dim yellow]")


def render_connection_error() -> None:
    console.print(
        Panel(
            "[bold red]Cannot connect to Ollama.[/bold red]\n\n"
            "Start the Ollama server:\n"
            "  [cyan]ollama serve[/cyan]\n\n"
            "Pull the model if needed:\n"
            f"  [cyan]ollama pull {config.MODEL_NAME}[/cyan]",
            title="[red]Connection Error[/red]",
            border_style="red",
        )
    )


def render_error(err: str) -> None:
    console.print(Panel(f"[red]{err}[/red]", title="[red]Error[/red]", border_style="red"))


def render_blank() -> None:
    console.print()


# --------------------------------------------------------------------------- #
# Demo mode rendering
# --------------------------------------------------------------------------- #


def render_demo_header(count: int) -> None:
    console.print(
        Panel(
            f"[bold]Running [magenta]{count}[/magenta] showcase scenarios[/bold]\n"
            "Each scenario highlights one or more agent tools.",
            title="[bold magenta]DEMO MODE[/bold magenta]",
            border_style="magenta",
        )
    )
    console.print()


def render_scenario_rule(idx: int, total: int, title: str, highlight: str) -> None:
    console.print(
        Rule(
            f"[bold magenta]Scenario {idx}/{total} — {title}[/bold magenta]",
            style="magenta",
        )
    )
    console.print(f"  [dim]Tools: {highlight}[/dim]")
    console.print()


def render_scenario_pause(is_last: bool) -> bool:
    """Prompt user to press Enter between scenarios. Returns False if interrupted."""
    if is_last:
        return True
    try:
        console.print("[dim]  Press [bold]Enter[/bold] for next scenario…[/dim]")
        input()
        return True
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Demo interrupted.[/yellow]")
        return False


def render_demo_complete() -> None:
    console.print(Rule("[bold green]Demo Complete[/bold green]", style="green"))


def render_demo_results_table(results: list[dict]) -> None:
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


# --------------------------------------------------------------------------- #
# Interactive mode rendering
# --------------------------------------------------------------------------- #


def render_welcome() -> None:
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


def render_help() -> None:
    console.print(Panel(Markdown(HELP_TEXT), border_style="yellow", title="[yellow]Help[/yellow]"))


def render_goodbye() -> None:
    console.print("[yellow]Goodbye![/yellow]")


def render_interrupted() -> None:
    console.print("\n[yellow]Bye![/yellow]")


def prompt_user() -> str:
    return console.input("[bold cyan]You ›[/bold cyan] ").strip()


__all__ = [
    "console",
    "strip_thinking",
    "fmt_args",
    "preview",
    "print_banner",
    "render_initialising",
    "render_ready",
    "render_init_error",
    "render_user_query",
    "render_thinking",
    "render_tool_call",
    "render_tool_result",
    "render_final_answer",
    "render_no_answer",
    "render_connection_error",
    "render_error",
    "render_blank",
    "render_demo_header",
    "render_scenario_rule",
    "render_scenario_pause",
    "render_demo_complete",
    "render_demo_results_table",
    "render_welcome",
    "render_help",
    "render_goodbye",
    "render_interrupted",
    "prompt_user",
    "DEMO_SCENARIOS",
    "HELP_TEXT",
]
