# AI Agent Demo

A multi-tool AI agent built with **LangChain + LangGraph + Ollama**, running the `qwen3.5` model entirely locally — no cloud API keys required.

## Features

| Tool | What it does |
|---|---|
| `calculator` | Safe arithmetic & math functions (`sqrt`, `sin`, `log`, `pow`, …) |
| `get_current_datetime` | Current date/time in any timezone, day-of-week, week number |
| `get_weather` | Live weather for any city via [wttr.in](https://wttr.in) (no API key) |
| `wikipedia_search` | Factual knowledge summaries from Wikipedia |
| `unit_converter` | Length, mass, speed, temperature, area, volume, data, time |

The agent chains tools together automatically to answer complex, multi-step questions.

## Requirements

- Python 3.12+
- [Ollama](https://ollama.com) running locally
- `qwen3.5` model pulled in Ollama

## Setup

```bash
# 1. Activate the Python environment
pyenv activate agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Copy and customise settings
cp .env.example .env

# 4. Make sure Ollama is running and the model is available
ollama serve &
ollama pull qwen3.5
```

## Usage

```bash
# Interactive chat (default)
python main.py

# Automated showcase — runs 7 pre-built scenarios
python main.py --demo

# Single one-shot query
python main.py -q "What is sqrt(2) raised to the power of 10?"
```

### Interactive commands

| Command | Action |
|---|---|
| `demo` | Run all showcase scenarios |
| `help` | Show example queries |
| `quit` / `exit` | Exit |

## Example queries

```
What is 15% of $1,247.50?
What day of the week is today and how many days remain in this year?
Compare the weather in Tokyo and London right now.
Explain the theory of relativity in simple terms.
Convert 90 mph to km/h and m/s.
A marathon is 42.195 km — if I run at 11 km/h, how long will it take in hours and minutes?
```

## Configuration

Copy `.env.example` to `.env` and adjust as needed:

```env
OLLAMA_BASE_URL=http://localhost:11434
MODEL_NAME=qwen3.5
TEMPERATURE=0.1
MAX_ITERATIONS=15
```

## Architecture

```
main.py               ← CLI entry point, Rich UI, streaming display
agent/
  core.py             ← LangGraph create_react_agent + system prompt
  tools.py            ← @tool definitions (5 tools)
  config.py           ← env-based configuration
  __init__.py
```

The agent uses LangGraph's **ReAct** loop: the model autonomously decides which tools to call, in what order, and how many times — until it can produce a final answer.
