from __future__ import annotations

import pytest

from meeting_minutes.config import ConfigurationError, load_settings, validate_settings


def test_validate_settings_missing_openai_key(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("meeting_minutes.config.load_dotenv", lambda *_a, **_k: False)
    settings = load_settings()

    with pytest.raises(ConfigurationError, match="OPENAI_API_KEY"):
        validate_settings(settings)
