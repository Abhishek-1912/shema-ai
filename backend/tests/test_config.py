import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.fixture
def required_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Set every required variable to a fake value; tests can then change or remove one."""
    monkeypatch.setenv("LLM_API_KEY", "test-key-123")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("SUPABASE_URL", "https://fake-project.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "fake-supabase-secret-456")
    return monkeypatch


def test_settings_load_from_environment(required_env: pytest.MonkeyPatch) -> None:
    settings = Settings(_env_file=None)

    assert settings.llm_model == "test-model"
    assert settings.llm_api_key.get_secret_value() == "test-key-123"
    assert settings.supabase_url == "https://fake-project.supabase.co"
    assert settings.supabase_secret_key.get_secret_value() == "fake-supabase-secret-456"


def test_secrets_are_hidden_when_printed(required_env: pytest.MonkeyPatch) -> None:
    settings = Settings(_env_file=None)

    for secret in ("test-key-123", "fake-supabase-secret-456"):
        assert secret not in str(settings)
        assert secret not in repr(settings)


@pytest.mark.parametrize("variable", ["LLM_API_KEY", "LLM_MODEL", "SUPABASE_URL", "SUPABASE_SECRET_KEY"])
def test_missing_required_variable_raises_error(
    required_env: pytest.MonkeyPatch, variable: str
) -> None:
    required_env.delenv(variable)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
