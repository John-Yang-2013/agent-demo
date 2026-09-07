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


def test_stage2_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Memory window, cache TTLs and context limits are env-configurable."""
    monkeypatch.setenv("HISTORY_MAX_MESSAGES", "6")
    monkeypatch.setenv("WEATHER_CACHE_TTL", "30")
    monkeypatch.setenv("NUM_CTX", "4096")
    cfg = AgentConfig(**_env_overrides())
    assert cfg.HISTORY_MAX_MESSAGES == 6
    assert cfg.WEATHER_CACHE_TTL == 30
    assert cfg.NUM_CTX == 4096


def test_stage2_defaults_and_validation() -> None:
    cfg = AgentConfig()
    assert cfg.HISTORY_MAX_MESSAGES == 12
    assert cfg.WEATHER_CACHE_TTL == 600
    assert cfg.WIKIPEDIA_CACHE_TTL == 3600
    assert cfg.NUM_CTX == 8192
    assert cfg.NUM_PREDICT == 4096
    with pytest.raises(ValidationError):
        AgentConfig(NUM_CTX=128)  # below ge=512
