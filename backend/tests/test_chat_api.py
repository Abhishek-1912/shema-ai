"""API tests for POST /api/chat (contract v2: docs/api-contract.md).

ChatService is replaced with a fake via FastAPI's dependency_overrides, so these
tests check only the HTTP layer: validation, response shape and error mapping.
"""

from collections.abc import Iterator
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.conversation_repository import ConversationNotFoundError, RepositoryError
from app.routers.chat import get_chat_service
from app.services.chat_service import ChatService, ChatTurn
from app.services.llm_service import (
    LLMConfigurationError,
    LLMRateLimitError,
    LLMServiceError,
    LLMUnavailableError,
)
from tests.factories import make_message

client = TestClient(app)

CONVERSATION_ID = uuid4()


@pytest.fixture
def fake_chat() -> Iterator[MagicMock]:
    fake = MagicMock(spec=ChatService)
    fake.send_message.return_value = ChatTurn(
        conversation_id=CONVERSATION_ID,
        user_message=make_message(CONVERSATION_ID, "user", "What is an LLM?"),
        assistant_message=make_message(
            CONVERSATION_ID, "assistant", "A language model.", with_usage=True
        ),
    )
    app.dependency_overrides[get_chat_service] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


# --- Success ----------------------------------------------------------------

def test_new_conversation_returns_contract_shape(fake_chat: MagicMock) -> None:
    response = client.post("/api/chat", json={"message": "What is an LLM?"})

    assert response.status_code == 200
    body = response.json()
    assert body["conversation_id"] == str(CONVERSATION_ID)

    assert body["user_message"]["role"] == "user"
    assert body["user_message"]["content"] == "What is an LLM?"
    assert body["user_message"]["model"] is None
    assert body["user_message"]["usage"] is None

    assert body["assistant_message"]["role"] == "assistant"
    assert body["assistant_message"]["model"] == "fake-model"
    assert body["assistant_message"]["usage"] == {
        "input_tokens": 10,
        "output_tokens": 6,
        "thinking_tokens": 4,
        "total_tokens": 20,
    }
    assert set(body["assistant_message"]) == {"id", "role", "content", "created_at", "model", "usage"}

    fake_chat.send_message.assert_called_once_with("What is an LLM?", None)


def test_existing_conversation_id_is_passed_to_service(fake_chat: MagicMock) -> None:
    client.post(
        "/api/chat",
        json={"conversation_id": str(CONVERSATION_ID), "message": "Give me an example."},
    )

    fake_chat.send_message.assert_called_once_with("Give me an example.", CONVERSATION_ID)


# --- Validation (422) ---------------------------------------------------------

@pytest.mark.parametrize(
    "body",
    [
        pytest.param({}, id="missing message"),
        pytest.param({"message": "   "}, id="blank message"),
        pytest.param({"message": "x" * 8001}, id="message too long"),
        pytest.param({"conversation_id": "not-a-uuid", "message": "Hi"}, id="bad conversation id"),
        pytest.param({"messages": [{"role": "user", "content": "Hi"}]}, id="old v1 body"),
    ],
)
def test_invalid_body_returns_422_without_calling_service(fake_chat: MagicMock, body: dict) -> None:
    response = client.post("/api/chat", json=body)

    assert response.status_code == 422
    fake_chat.send_message.assert_not_called()


def test_message_of_exactly_8000_characters_is_allowed(fake_chat: MagicMock) -> None:
    response = client.post("/api/chat", json={"message": "x" * 8000})

    assert response.status_code == 200


# --- Error mapping --------------------------------------------------------------

@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        pytest.param(ConversationNotFoundError(CONVERSATION_ID), 404, id="unknown conversation"),
        pytest.param(LLMRateLimitError("quota"), 429, id="rate limit"),
        pytest.param(LLMConfigurationError("Model 'x' was not found."), 500, id="bad config"),
        pytest.param(LLMServiceError("empty reply"), 502, id="unexpected"),
        pytest.param(LLMUnavailableError("timeout"), 503, id="llm unavailable"),
        pytest.param(RepositoryError("connection refused"), 503, id="database unavailable"),
    ],
)
def test_errors_map_to_http_status(fake_chat: MagicMock, error: Exception, expected_status: int) -> None:
    fake_chat.send_message.side_effect = error

    response = client.post("/api/chat", json={"message": "Hi"})

    assert response.status_code == expected_status
    detail = response.json()["detail"]
    assert isinstance(detail, str) and detail  # the frontend shows this text


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(LLMConfigurationError("The LLM API key fake-gemini-secret was rejected."), id="llm"),
        pytest.param(RepositoryError("Database rejected the request: fake-internal-detail"), id="db"),
    ],
)
def test_errors_do_not_leak_internal_details(fake_chat: MagicMock, error: Exception) -> None:
    fake_chat.send_message.side_effect = error

    response = client.post("/api/chat", json={"message": "Hi"})

    assert "fake-gemini-secret" not in response.text
    assert "fake-internal-detail" not in response.text
