"""CENTRALIZED CONFIG"""
from __future__ import annotations
from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv(override=True)


@dataclass(frozen=True)
class AppConfig:
    provider: str = os.getenv("SELECTED_PROVIDER", "OLLAMA")

    API_KEY:    str | None = None
    URL:        str | None = None
    MODEL_NAME: str | None = None

    if provider == "OLLAMA":
        URL        = "http://localhost:11434/v1"
        API_KEY    = "OLLAMA"
        MODEL_NAME = os.getenv("OLLAMA_MODEL")
    elif provider == "OPENROUTER":
        URL        = "https://openrouter.ai/api/v1"
        API_KEY    = os.getenv("OPENROUTER_API_KEY")
        MODEL_NAME = os.getenv("OPENROUTER_MODEL")
    else:
        API_KEY    = os.getenv("OPENAI_API_KEY")
        MODEL_NAME = os.getenv("OPENAI_MODEL")

    output_dir: str = os.getenv("OUTPUT_DIR", "output")


def validate_config(cfg: AppConfig) -> list[str]:
    warnings: list[str] = []
    if not cfg.API_KEY:
        warnings.append("API key not set. Model calls will fail.")
    if cfg.provider in ("OLLAMA", "OPENROUTER") and not cfg.URL:
        warnings.append("Base URL not set for provider.")
    if not cfg.MODEL_NAME:
        warnings.append("MODEL_NAME not set.")
    return warnings
