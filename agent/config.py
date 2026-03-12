"""Configuration loaded from environment variables or .env file."""

import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME: str = os.getenv("MODEL_NAME", "qwen3.5")
TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.1"))
MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "15"))
RECURSION_LIMIT: int = MAX_ITERATIONS * 2 + 1
