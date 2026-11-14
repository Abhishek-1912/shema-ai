from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All app configuration, read from environment variables or the .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General
    app_name: str = "Shema AI"
    environment: str = "development"

    # LLM provider (Gemini via its OpenAI-compatible endpoint)
    llm_api_key: SecretStr
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    llm_model: str
    llm_timeout_seconds: float = 30.0


@lru_cache
def get_settings() -> Settings:
    """Create Settings once and reuse the same object everywhere."""
    return Settings()
