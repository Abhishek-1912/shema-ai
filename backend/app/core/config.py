from functools import lru_cache
from typing import Literal

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

    # Embeddings (same provider and key as the LLM)
    embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 768

    # Chunking (characters; ~4 characters ≈ 1 token)
    chunk_max_chars: int = 500
    chunk_overlap_chars: int = 100

    # Retrieval: "hybrid" = keywords + meaning (default), "vector" = meaning only
    search_mode: Literal["hybrid", "vector"] = "hybrid"

    # Agent: write a step-by-step plan (one extra AI call) before using tools
    agent_planning: bool = True

    # Supabase (backend only: the secret key bypasses Row Level Security)
    supabase_url: str
    supabase_secret_key: SecretStr


@lru_cache
def get_settings() -> Settings:
    """Create Settings once and reuse the same object everywhere."""
    return Settings()
