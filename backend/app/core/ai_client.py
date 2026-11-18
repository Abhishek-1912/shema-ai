from functools import lru_cache

from openai import AsyncOpenAI, OpenAI

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


def create_async_ai_client() -> AsyncOpenAI:
    """A NEW async client, for code that runs inside an event loop (the MCP tool agent).

    Deliberately NOT cached: an async client's connections belong to the event loop that
    created them. Sharing one across loops fails with "Event loop is closed" (found in an
    end-to-end test). Create one per agent run and close it afterwards.
    """
    settings = get_settings()
    return AsyncOpenAI(
        api_key=settings.llm_api_key.get_secret_value(),
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout_seconds,
        max_retries=2,
    )
