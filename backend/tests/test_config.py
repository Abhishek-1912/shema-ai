import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_load_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key-123")
    monkeypatch.setenv("LLM_MODEL", "test-model")

    settings = Settings(_env_file=None)

    assert settings.llm_model == "test-model"
    assert settings.llm_api_key.get_secret_value() == "test-key-123"


def test_api_key_is_hidden_when_printed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key-123")
    monkeypatch.setenv("LLM_MODEL", "test-model")

    settings = Settings(_env_file=None)

    assert "test-key-123" not in str(settings)
    assert "test-key-123" not in repr(settings)


def test_missing_api_key_raises_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("LLM_MODEL", "test-model")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
