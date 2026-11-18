"""Unit tests for LLMService.

These tests NEVER call Gemini. We replace the OpenAI client with a fake (a "mock"),
so the tests are fast, free, and work without internet.
"""

from unittest.mock import MagicMock

import httpx
import openai
import pytest
from openai.types.chat import ChatCompletion

from app.services.llm_service import (
    ChatMessage,
    LLMConfigurationError,
    LLMRateLimitError,
    LLMService,
    LLMServiceError,
    LLMUnavailableError,
)

FAKE_REQUEST = httpx.Request("POST", "https://fake-llm.test/chat/completions")


def make_completion(content: str | None, prompt: int = 10, completion: int = 5, total: int = 40) -> ChatCompletion:
    """Build a realistic response object, exactly like the SDK would return."""
    return ChatCompletion.model_validate(
        {
            "id": "test-123",
            "object": "chat.completion",
            "created": 0,
            "model": "fake-model",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
            "usage": {
                "prompt_tokens": prompt,
                "completion_tokens": completion,
                "total_tokens": total,
            },
        }
    )


def make_service(fake_client: MagicMock) -> LLMService:
    return LLMService(client=fake_client, model="fake-model", system_prompt="Be nice.")


def make_status_error(error_class: type[openai.APIStatusError], status: int) -> openai.APIStatusError:
    response = httpx.Response(status, request=FAKE_REQUEST)
    return error_class(message="fake error", response=response, body=None)


# --- Happy path -------------------------------------------------------------

def test_chat_returns_content_and_usage() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = make_completion(
        "Hello from the fake model!", prompt=10, completion=5, total=40
    )

    result = make_service(fake_client).chat([ChatMessage(role="user", content="Hi")])

    assert result.content == "Hello from the fake model!"
    assert result.model == "fake-model"
    assert result.usage is not None
    assert result.usage.input_tokens == 10
    assert result.usage.output_tokens == 5
    assert result.usage.thinking_tokens == 25  # 40 - 10 - 5
    assert result.usage.total_tokens == 40


def test_chat_sends_system_prompt_first_then_conversation() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = make_completion("ok")

    make_service(fake_client).chat(
        [
            ChatMessage(role="user", content="My name is Abhi"),
            ChatMessage(role="assistant", content="Nice to meet you!"),
            ChatMessage(role="user", content="What is my name?"),
        ]
    )

    # Inspect exactly what our service sent to the (fake) client.
    sent = fake_client.chat.completions.create.call_args.kwargs
    assert sent["model"] == "fake-model"
    assert sent["messages"] == [
        {"role": "system", "content": "Be nice."},
        {"role": "user", "content": "My name is Abhi"},
        {"role": "assistant", "content": "Nice to meet you!"},
        {"role": "user", "content": "What is my name?"},
    ]


def test_custom_system_prompt_replaces_the_default_for_one_call() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = make_completion("ok")

    make_service(fake_client).chat(
        [ChatMessage(role="user", content="Hi")], system_prompt="Answer only from sources."
    )

    sent = fake_client.chat.completions.create.call_args.kwargs["messages"]
    assert sent[0] == {"role": "system", "content": "Answer only from sources."}


# --- Error handling ---------------------------------------------------------

def test_empty_reply_raises_service_error() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = make_completion(None)

    with pytest.raises(LLMServiceError):
        make_service(fake_client).chat([ChatMessage(role="user", content="Hi")])


def test_rate_limit_is_translated() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = make_status_error(openai.RateLimitError, 429)

    with pytest.raises(LLMRateLimitError):
        make_service(fake_client).chat([ChatMessage(role="user", content="Hi")])


def test_bad_api_key_is_translated() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = make_status_error(openai.AuthenticationError, 401)

    with pytest.raises(LLMConfigurationError):
        make_service(fake_client).chat([ChatMessage(role="user", content="Hi")])


def test_unknown_model_is_translated() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = make_status_error(openai.NotFoundError, 404)

    with pytest.raises(LLMConfigurationError, match="fake-model"):
        make_service(fake_client).chat([ChatMessage(role="user", content="Hi")])


def test_timeout_is_translated_with_clear_message() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = openai.APITimeoutError(request=FAKE_REQUEST)

    with pytest.raises(LLMUnavailableError, match="did not answer in time"):
        make_service(fake_client).chat([ChatMessage(role="user", content="Hi")])


def test_overloaded_provider_503_is_translated() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = make_status_error(openai.InternalServerError, 503)

    with pytest.raises(LLMUnavailableError, match="503"):
        make_service(fake_client).chat([ChatMessage(role="user", content="Hi")])


def test_network_failure_is_translated() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = openai.APIConnectionError(request=FAKE_REQUEST)

    with pytest.raises(LLMUnavailableError):
        make_service(fake_client).chat([ChatMessage(role="user", content="Hi")])
