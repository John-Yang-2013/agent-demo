# GitHub Copilot Instructions

## Project Overview

**Repository:** `agent-demo`
**Language & runtime:** Python 3.12 (managed with `pyenv`; local version pin `3.12.11`)
**Purpose:** An interactive AI agent demo built with LangChain + LangGraph that runs a local
LLM via Ollama. It exposes a multi-tool ReAct agent through a rich terminal UI with three
run modes: interactive chat, single-shot query, and an automated demo showcase.

---

## Architecture

```
agent-demo/
├── main.py              # Entry point — CLI arg parsing, Rich UI, demo runner
├── requirements.txt     # Python dependencies
├── .env                 # (gitignored) local config overrides
└── agent/
    ├── __init__.py
    ├── config.py        # Loads env vars: MODEL_NAME, OLLAMA_BASE_URL, TEMPERATURE, etc.
    ├── core.py          # Builds the LangGraph ReAct agent with ChatOllama + TOOLS
    └── tools.py         # All LangChain @tool definitions (5 tools)
```

### Key components

| File | Responsibility |
|---|---|
| `main.py` | Argparse (`--demo`, `-q`), Rich console panels, streaming message loop |
| `agent/config.py` | Central config via `python-dotenv`; runtime-tunable via env vars |
| `agent/core.py` | Instantiates `ChatOllama`, injects `SYSTEM_PROMPT`, calls `create_react_agent` |
| `agent/tools.py` | Defines and exports `TOOLS` list with all 5 agent tools |

### LLM & framework

- **LLM backend:** Ollama (default: `http://localhost:11434`), model `qwen3.5`
- **Agent type:** LangGraph `create_react_agent` (ReAct loop, configurable recursion limit)
- **Orchestration:** LangChain Core + LangChain Ollama + LangGraph
- **UI:** `rich` (panels, tables, markdown rendering, spinner)

### Agent tools (`agent/tools.py`)

| Tool | Description |
|---|---|
| `calculator` | Safe AST-based arithmetic evaluator; supports math functions (`sqrt`, `sin`, `log`, …) |
| `get_current_datetime` | Current date/time in any IANA timezone, day-of-week, week number, countdown |
| `get_weather` | Real-time weather via `wttr.in` (no API key required) |
| `wikipedia_search` | Wikipedia article summary lookup |
| `unit_converter` | Converts length, mass, speed, temperature, area, volume, data, time |

### Configuration (`agent/config.py`)

All values are overridable via environment variables or `.env`:

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `MODEL_NAME` | `qwen3.5` | Ollama model to load |
| `TEMPERATURE` | `0.1` | LLM sampling temperature |
| `MAX_ITERATIONS` | `15` | Max ReAct loop steps; `RECURSION_LIMIT = MAX_ITERATIONS * 2 + 1` |

### Dependencies (`requirements.txt`)

```
langchain>=0.3.0
langchain-core>=0.3.0
langchain-ollama>=0.2.0
langgraph>=0.2.0
requests>=2.31.0
wikipedia>=1.4.0
rich>=13.7.0
python-dotenv>=1.0.0
```

---

## Run modes

```bash
# Interactive chat (REPL)
python main.py

# Single-shot query
python main.py -q "Convert 100 mph to km/h"

# Automated demo (runs all 7 showcase scenarios)
python main.py --demo
```

### Quick local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Ensure Ollama is running and qwen3.5 is pulled
ollama pull qwen3.5
python main.py
```

---

## Copilot / assistant guidelines

- Follow the project's existing style and patterns.
- Match the tool-definition pattern in `agent/tools.py` when adding new tools: decorate with `@tool`, include a detailed docstring with args and examples, and add to the `TOOLS` list.
- When modifying the agent system prompt in `agent/core.py`, keep the bullet-list format and update the "Available tools" section to stay in sync with `tools.py`.
- Add type hints on all new function signatures.
- Keep functions small and single-responsibility.
- Avoid changing unrelated files or reformatting large sections of code.
- If unsure about a breaking change, propose alternatives and explain the trade-offs.

---

## Commit message format

We follow a concise, structured format inspired by Conventional Commits.

**Structure:**
```
<type>(<scope>): <short summary (≤50 chars, present tense)>

<body — explain the why, wrap at 72 chars> (optional)

<footer — issue refs or BREAKING CHANGE> (optional)
```

**Types:**

| Type | When to use |
|---|---|
| `feat` | New feature or new tool |
| `fix` | Bug fix |
| `docs` | Documentation-only changes |
| `style` | Formatting, no logic change |
| `refactor` | Code restructure, no behaviour change |
| `perf` | Performance improvement |
| `test` | Adding or fixing tests |
| `chore` | Maintenance: deps, tooling, config |

**Scope examples** (use the module/area affected):
`tools`, `core`, `config`, `main`, `deps`, `docs`, `ci`

**Examples:**
```
feat(tools): add currency_converter tool
fix(core): handle empty tool response in ReAct loop
chore(deps): bump langchain to 0.3.5
docs: add setup instructions for Windows
refactor(config): replace os.getenv with pydantic-settings
```

**Footer refs:**
```
Refs #42
Fixes #17
BREAKING CHANGE: TOOLS list signature changed; update callers
```

When generating commit messages, always prefer a descriptive subject and a body that explains the reasoning behind the change.
