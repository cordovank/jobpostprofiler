"""CENTRALIZED CONFIG"""
from __future__ import annotations
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Repo root: two levels up from src/jobpostprofiler/config.py
REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_PATH = REPO_ROOT / "my_skills.json"
DB_PATH = REPO_ROOT / "jobs.db"

_profile_cache: dict[str, tuple[float, dict]] = {}


def load_user_profile(path: Path = SKILLS_PATH) -> Optional[dict]:
    """Load and cache user skills profile. Returns None if file
    doesn't exist. Re-reads if file modification time changed."""
    if not path.exists():
        return None
    key = str(path)
    mtime = path.stat().st_mtime
    cached = _profile_cache.get(key)
    if cached and cached[0] == mtime:
        return cached[1]
    profile = json.loads(path.read_text(encoding="utf-8"))
    _profile_cache[key] = (mtime, profile)
    return profile

load_dotenv(override=True)


@dataclass(frozen=True)
class AppConfig:
    provider:       str       = field(default_factory=lambda: os.getenv("SELECTED_PROVIDER", "OLLAMA"))
    source_channel: str       = field(default_factory=lambda: os.getenv("SOURCE_CHANNEL", "other"))
    model_override: str|None  = None
    URL:            str|None  = field(init=False, default=None)
    API_KEY:        str|None  = field(init=False, default=None)
    MODEL_NAME:     str|None  = field(init=False, default=None)

    def __post_init__(self):
        if self.provider == "OLLAMA":
            object.__setattr__(self, "URL",        "http://localhost:11434/v1")
            object.__setattr__(self, "API_KEY",    "OLLAMA")
            object.__setattr__(self, "MODEL_NAME", os.getenv("OLLAMA_MODEL"))
        elif self.provider == "OPENROUTER":
            object.__setattr__(self, "URL",        "https://openrouter.ai/api/v1")
            object.__setattr__(self, "API_KEY",    os.getenv("OPENROUTER_API_KEY"))
            object.__setattr__(self, "MODEL_NAME", os.getenv("OPENROUTER_MODEL"))
        else:  # OPENAI
            object.__setattr__(self, "URL",        None)
            object.__setattr__(self, "API_KEY",    os.getenv("OPENAI_API_KEY"))
            object.__setattr__(self, "MODEL_NAME", os.getenv("OPENAI_MODEL"))

        if self.model_override:
            object.__setattr__(self, "MODEL_NAME", self.model_override)


def validate_config(cfg: AppConfig) -> list[str]:
    warnings: list[str] = []
    if not cfg.API_KEY:
        warnings.append("API key not set. Model calls will fail.")
    if cfg.provider in ("OLLAMA", "OPENROUTER") and not cfg.URL:
        warnings.append("Base URL not set for provider.")
    if not cfg.MODEL_NAME:
        warnings.append("MODEL_NAME not set.")
    return warnings
