from functools import lru_cache

from openai import OpenAI

from app.core.config import get_settings


@lru_cache
def get_ai_client() -> OpenAI:
    """ONE OpenAI-SDK client (pointed at Gemini) shared by the LLM and embedding services.

    Sharing it means one connection pool and one place for timeout/retry settings.
    """
    settings = get_settings()
    return OpenAI(
        api_key=settings.llm_api_key.get_secret_value(),
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout_seconds,
        max_retries=2,
    )
