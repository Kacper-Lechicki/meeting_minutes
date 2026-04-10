from __future__ import annotations

import os

from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv


class ConfigurationError(ValueError):
    """Invalid or missing configuration (e.g. API key)."""


@dataclass(frozen=True)
class Settings:
    openai_api_key: Optional[str]
    whisper_model: str
    llm_model: str
    llm_max_output_tokens: int
    max_audio_size_mb: int
    debug: bool


def _get_env(name: str) -> Optional[str]:
    value = os.environ.get(name)

    if value is None:
        return None

    value = value.strip()

    return value or None


def load_settings() -> Settings:
    """
    Loads settings from environment/.env (local-only).

    Keys (aligned with notebooks/meeting_minutes.ipynb):
    - OPENAI_API_KEY (required)
    - WHISPER_MODEL (default whisper-1)
    - LLM_MODEL (default gpt-4o-mini)
    - LLM_MAX_OUTPUT_TOKENS (default 5000; notebook uses 5000)
    - MAX_AUDIO_SIZE_MB (default 25)
    - DEBUG (optional)

    Security note: this function never prints secret values.
    """

    load_dotenv(override=True)

    openai_api_key = _get_env("OPENAI_API_KEY")
    whisper_model = _get_env("WHISPER_MODEL") or "whisper-1"
    llm_model = _get_env("LLM_MODEL") or "gpt-4o-mini"

    try:
        llm_max_output_tokens = int(_get_env("LLM_MAX_OUTPUT_TOKENS") or "5000")
    except ValueError:
        llm_max_output_tokens = 5000

    try:
        max_audio_size_mb = int(_get_env("MAX_AUDIO_SIZE_MB") or "25")
    except ValueError:
        max_audio_size_mb = 25

    debug = (_get_env("DEBUG") or "").lower() in ("1", "true", "yes", "y", "on")

    return Settings(
        openai_api_key=openai_api_key,
        whisper_model=whisper_model,
        llm_model=llm_model,
        llm_max_output_tokens=llm_max_output_tokens,
        max_audio_size_mb=max_audio_size_mb,
        debug=debug,
    )


def validate_settings(settings: Settings) -> None:
    if not settings.openai_api_key:
        raise ConfigurationError(
            "Missing OPENAI_API_KEY. Set it in your environment or a local .env file."
        )
