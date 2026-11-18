"""LLM service: the ONE place in the backend that talks to the language model.

Routers, agents and RAG code call this service; they never call the OpenAI SDK directly.
That way, changing provider, model, retries or logging happens in one file.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from typing import Literal

import openai
from openai import OpenAI
from pydantic import BaseModel

from app.core.ai_client import get_ai_client
from app.core.config import get_settings

DEFAULT_SYSTEM_PROMPT = (
    "You are Shema AI, a friendly knowledge assistant. "
    "Explain things simply and clearly. If you are not sure about something, say so."
)


# ---------------------------------------------------------------------------
# Data types (what goes in and what comes out of the service)
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class TokenUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    thinking_tokens: int
    total_tokens: int


class LLMResult(BaseModel):
    content: str
    model: str
    usage: TokenUsage | None = None


# ---------------------------------------------------------------------------
# Our own errors, so the rest of the app never depends on OpenAI SDK exceptions
# ---------------------------------------------------------------------------

class LLMServiceError(Exception):
    """Base class for every LLM failure."""


class LLMConfigurationError(LLMServiceError):
    """Wrong API key or model name: a developer must fix .env."""


class LLMRateLimitError(LLMServiceError):
    """Too many requests or free-tier quota used up: try again later."""


class LLMUnavailableError(LLMServiceError):
    """Network problem or provider outage."""


@contextmanager
def translate_provider_errors(model: str) -> Iterator[None]:
    """Turn OpenAI SDK exceptions into our own errors. Shared by every AI service.

    Usage:
        with translate_provider_errors("gemini-..."):
            client.chat.completions.create(...)
    """
    try:
        yield
    except (openai.AuthenticationError, openai.PermissionDeniedError) as error:
        raise LLMConfigurationError("The AI provider API key was rejected.") from error
    except openai.NotFoundError as error:
        raise LLMConfigurationError(f"Model '{model}' was not found.") from error
    except openai.RateLimitError as error:
        raise LLMRateLimitError("AI provider rate limit or quota exceeded.") from error
    except openai.APITimeoutError as error:
        # Must come BEFORE APIConnectionError, because it is a subclass of it.
        raise LLMUnavailableError(
            f"Model '{model}' did not answer in time (it may be overloaded)."
        ) from error
    except openai.APIConnectionError as error:
        raise LLMUnavailableError("Could not reach the AI provider.") from error
    except openai.InternalServerError as error:
        raise LLMUnavailableError(
            f"Model '{model}' is temporarily unavailable (HTTP {error.status_code})."
        ) from error
    except openai.APIStatusError as error:
        raise LLMServiceError(f"AI provider returned HTTP {error.status_code}.") from error


# ---------------------------------------------------------------------------
# The service
# ---------------------------------------------------------------------------

class LLMService:
    def __init__(
        self,
        client: OpenAI,
        model: str,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        # The client is passed IN (dependency injection), so tests can pass a fake one.
        self._client = client
        self._model = model
        self._system_prompt = system_prompt

    def chat(self, messages: list[ChatMessage], system_prompt: str | None = None) -> LLMResult:
        """Send the conversation to the model and return its reply.

        `system_prompt` replaces the default instructions for this one call (RAG uses its own).
        """
        payload = [{"role": "system", "content": system_prompt or self._system_prompt}]
        payload += [message.model_dump() for message in messages]

        with translate_provider_errors(self._model):
            response = self._client.chat.completions.create(
                model=self._model,
                messages=payload,
            )

        content = response.choices[0].message.content
        if not content:
            raise LLMServiceError("The model returned an empty response.")

        return LLMResult(
            content=content,
            model=response.model,
            usage=self._read_usage(response),
        )

    @staticmethod
    def _read_usage(response) -> TokenUsage | None:
        usage = response.usage
        if usage is None:
            return None
        # Thinking models report hidden reasoning tokens only inside the total.
        thinking = max(usage.total_tokens - usage.prompt_tokens - usage.completion_tokens, 0)
        return TokenUsage(
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            thinking_tokens=thinking,
            total_tokens=usage.total_tokens,
        )


@lru_cache
def get_llm_service() -> LLMService:
    """Build the real service once (with the shared AI client) and reuse it."""
    return LLMService(client=get_ai_client(), model=get_settings().llm_model)
