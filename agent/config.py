"""Configuration loaded from environment variables or .env file, with validation."""

import os
from collections.abc import Mapping
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class AgentConfig(BaseModel):
    """Runtime configuration for the agent with validation."""

    # LLM connection
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434", description="Ollama server URL", pattern=r"^https?://"
    )
    MODEL_NAME: str = Field(default="qwen3.5", description="Name of the Ollama model to use")

    # Reasoning models (qwen3.5 etc.) — stream thinking separately from content.
    # Required for correct final answers with Ollama >=0.33 + thinking models:
    # without it the client drops the thinking channel and the model may emit
    # its whole answer into thinking, leaving content empty.
    MODEL_REASONING: bool = Field(
        default=True,
        description="Separate thinking channel (reasoning models); turn off for non-thinking models",
    )

    # LLM behavior
    TEMPERATURE: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="LLM sampling temperature (0.0=deterministic, 2.0=creative)",
    )

    # Agent control
    MAX_ITERATIONS: int = Field(
        default=15, ge=1, le=100, description="Max ReAct loop steps before giving up"
    )

    # Conversation memory (stage 2)
    HISTORY_MAX_MESSAGES: int = Field(
        default=12,
        ge=2,
        le=100,
        description="Sliding window (in messages) replayed to the LLM each turn",
    )

    # Tool result caches (seconds)
    WEATHER_CACHE_TTL: int = Field(
        default=600, ge=1, le=86400, description="TTL for cached weather lookups"
    )
    WIKIPEDIA_CACHE_TTL: int = Field(
        default=3600, ge=1, le=86400, description="TTL for cached Wikipedia summaries"
    )
    SEARCH_CACHE_TTL: int = Field(
        default=300, ge=1, le=86400, description="TTL for cached web-search results"
    )

    # Model context / generation limits
    NUM_CTX: int = Field(
        default=8192,
        ge=512,
        le=131072,
        description="Ollama context window — must fit history + tool traffic",
    )
    NUM_PREDICT: int = Field(
        default=4096, ge=128, le=32768, description="Max tokens the model may generate"
    )

    # Streaming & resilience (stage 2)
    STREAM_TOKENS: bool = Field(
        default=True, description="Stream answer tokens live (typewriter effect)"
    )
    LLM_RETRIES: int = Field(
        default=2, ge=0, le=5, description="Retries for transient LLM/network failures"
    )
    LLM_RETRY_DELAY: float = Field(
        default=1.0, ge=0.0, le=30.0, description="Base retry delay (s) — doubles each retry"
    )

    # File sandbox (stage 3)
    SANDBOX_ENABLED: bool = Field(
        default=True, description="Enable the read/write/list/delete file tools"
    )
    SANDBOX_DIR: str = Field(
        default="workspace",
        description="Sandbox root directory for file tools (relative or absolute)",
    )
    SANDBOX_CONFIRM: bool = Field(
        default=True,
        description="Ask a human before overwrite/delete (false = scripting mode, auto-allow)",
    )
    SANDBOX_MAX_READ_CHARS: int = Field(
        default=8000,
        ge=200,
        le=200_000,
        description="read_file truncation limit to protect the LLM context",
    )

    @property
    def RECURSION_LIMIT(self) -> int:
        """LangGraph recursion limit = MAX_ITERATIONS * 2 + 1."""
        return self.MAX_ITERATIONS * 2 + 1


# Environment variables that map 1:1 onto config fields (all uppercase).
# Set them in the shell or in `.env` before this module is first imported.
_ENV_FIELDS = (
    "OLLAMA_BASE_URL",
    "MODEL_NAME",
    "MODEL_REASONING",
    "TEMPERATURE",
    "MAX_ITERATIONS",
    "HISTORY_MAX_MESSAGES",
    "WEATHER_CACHE_TTL",
    "WIKIPEDIA_CACHE_TTL",
    "SEARCH_CACHE_TTL",
    "NUM_CTX",
    "NUM_PREDICT",
    "STREAM_TOKENS",
    "LLM_RETRIES",
    "LLM_RETRY_DELAY",
    "SANDBOX_ENABLED",
    "SANDBOX_DIR",
    "SANDBOX_CONFIRM",
    "SANDBOX_MAX_READ_CHARS",
)

_config: AgentConfig | None = None


def _env_overrides(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Collect env vars that map onto config fields (injectable for tests).

    Values stay as strings; pydantic coerces and validates them on construction.
    """
    source = os.environ if env is None else env
    return {name: source[name] for name in _ENV_FIELDS if name in source}


def get_config() -> AgentConfig:
    """Get or create the singleton config instance (env-aware)."""
    global _config
    if _config is None:
        _config = AgentConfig(**_env_overrides())
    return _config


# Shared singleton — use `from agent.config import config`.
config = get_config()
