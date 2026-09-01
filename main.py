#!/usr/bin/env python3
"""
AI Agent Demo
=============
LangChain + LangGraph + Ollama  ·  model: qwen3.5

Modes:
  python main.py              # interactive chat
  python main.py --demo       # run all showcase scenarios automatically
  python main.py -q "…"       # single-shot query

This file is a thin entry point: it parses CLI args, builds the agent, and
delegates to the orchestration layer in `agent/runner.py`. All presentation
lives in `agent/ui.py` and demo data in `agent/scenarios.py`.
"""

import argparse
import sys

from agent import runner, ui
from agent.core import create_agent


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
    parser.add_argument(
        "--query", "-q", type=str, metavar="QUERY", help="Run a single query and exit"
    )
    args = parser.parse_args()

    ui.print_banner()

    ui.render_initialising()
    try:
        agent, tools, recursion_limit = create_agent()
        ui.render_ready(tools)
    except Exception as exc:
        ui.render_init_error(exc)
        sys.exit(1)

    if args.query:
        runner.run_query(agent, args.query, recursion_limit=recursion_limit)
    elif args.demo:
        runner.run_demo_mode(agent, recursion_limit)
    else:
        runner.run_interactive_mode(agent, recursion_limit)


if __name__ == "__main__":
    main()
