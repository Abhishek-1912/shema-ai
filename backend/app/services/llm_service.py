"""LLM service: the ONE place in the backend that talks to the language model.

Routers, agents and RAG code call this service; they never call the OpenAI SDK directly.
That way, changing provider, model, retries or logging happens in one file.
"""

from functools import lru_cache
from typing import Literal

import openai
from openai import OpenAI
from pydantic import BaseModel

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

    def chat(self, messages: list[ChatMessage]) -> LLMResult:
        """Send the conversation to the model and return its reply."""
        payload = [{"role": "system", "content": self._system_prompt}]
        payload += [message.model_dump() for message in messages]

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=payload,
            )
        except (openai.AuthenticationError, openai.PermissionDeniedError) as error:
            raise LLMConfigurationError("The LLM API key was rejected.") from error
        except openai.NotFoundError as error:
            raise LLMConfigurationError(f"Model '{self._model}' was not found.") from error
        except openai.RateLimitError as error:
            raise LLMRateLimitError("LLM rate limit or quota exceeded.") from error
        except openai.APITimeoutError as error:
            # Must come BEFORE APIConnectionError, because it is a subclass of it.
            raise LLMUnavailableError(
                f"Model '{self._model}' did not answer in time (it may be overloaded)."
            ) from error
        except openai.APIConnectionError as error:
            raise LLMUnavailableError("Could not reach the LLM provider.") from error
        except openai.InternalServerError as error:
            raise LLMUnavailableError(
                f"Model '{self._model}' is temporarily unavailable "
                f"(HTTP {error.status_code})."
            ) from error
        except openai.APIStatusError as error:
            raise LLMServiceError(
                f"LLM provider returned HTTP {error.status_code}."
            ) from error

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
    """Build the real service once (with the real OpenAI client) and reuse it."""
    settings = get_settings()
    client = OpenAI(
        api_key=settings.llm_api_key.get_secret_value(),
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout_seconds,
        max_retries=2,
    )
    return LLMService(client=client, model=settings.llm_model)
