"""Tests for env-driven, validated configuration loading."""

import pytest
from pydantic import ValidationError

from agent.config import AgentConfig, _env_overrides


def test_defaults() -> None:
    cfg = AgentConfig()
    assert cfg.OLLAMA_BASE_URL == "http://localhost:11434"
    assert cfg.MODEL_NAME == "qwen3.5"
    assert cfg.TEMPERATURE == 0.1
    assert cfg.MAX_ITERATIONS == 15
    assert cfg.RECURSION_LIMIT == 31  # MAX_ITERATIONS * 2 + 1


def test_env_overrides_only_picks_known_fields() -> None:
    env = {
        "OLLAMA_BASE_URL": "http://gpu-box:11434",
        "TEMPERATURE": "0.7",
        "MAX_ITERATIONS": "5",
        "UNRELATED": "ignored",
    }
    assert _env_overrides(env) == {
        "OLLAMA_BASE_URL": "http://gpu-box:11434",
        "TEMPERATURE": "0.7",
        "MAX_ITERATIONS": "5",
    }


def test_string_env_values_are_coerced() -> None:
    cfg = AgentConfig(**_env_overrides({"TEMPERATURE": "0.7", "MAX_ITERATIONS": "5"}))
    assert cfg.TEMPERATURE == 0.7
    assert cfg.MAX_ITERATIONS == 5
    assert cfg.RECURSION_LIMIT == 11


def test_out_of_range_temperature_rejected() -> None:
    with pytest.raises(ValidationError):
        AgentConfig(TEMPERATURE=2.5)


def test_invalid_url_scheme_rejected() -> None:
    with pytest.raises(ValidationError):
        AgentConfig(OLLAMA_BASE_URL="ftp://nope")
