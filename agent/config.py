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

    @property
    def RECURSION_LIMIT(self) -> int:
        """LangGraph recursion limit = MAX_ITERATIONS * 2 + 1."""
        return self.MAX_ITERATIONS * 2 + 1


# Environment variables that map 1:1 onto config fields (all uppercase).
# Set them in the shell or in `.env` before this module is first imported.
_ENV_FIELDS = ("OLLAMA_BASE_URL", "MODEL_NAME", "TEMPERATURE", "MAX_ITERATIONS")

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
