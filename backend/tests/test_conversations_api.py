"""API tests for /api/conversations endpoints (contract v2). The repository is a mock."""

from collections.abc import Iterator
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.conversation_repository import (
    ConversationRepository,
    RepositoryError,
    get_conversation_repository,
)
from tests.factories import make_conversation, make_message

client = TestClient(app)


@pytest.fixture
def fake_repo() -> Iterator[MagicMock]:
    fake = MagicMock(spec=ConversationRepository)
    app.dependency_overrides[get_conversation_repository] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


# --- GET /api/conversations -----------------------------------------------------

def test_list_conversations(fake_repo: MagicMock) -> None:
    first, second = make_conversation(title="Newest"), make_conversation(title="Older")
    fake_repo.list_conversations.return_value = [first, second]

    response = client.get("/api/conversations")

    assert response.status_code == 200
    conversations = response.json()["conversations"]
    assert [c["title"] for c in conversations] == ["Newest", "Older"]
    assert set(conversations[0]) == {"id", "title", "created_at", "updated_at"}
    fake_repo.list_conversations.assert_called_once_with(limit=50)


def test_list_is_empty_when_no_conversations(fake_repo: MagicMock) -> None:
    fake_repo.list_conversations.return_value = []

    response = client.get("/api/conversations")

    assert response.json() == {"conversations": []}


# --- GET /api/conversations/{id} --------------------------------------------------

def test_get_conversation_with_messages(fake_repo: MagicMock) -> None:
    conversation = make_conversation(title="What is an LLM?")
    fake_repo.get_conversation.return_value = conversation
    fake_repo.get_messages.return_value = [
        make_message(conversation.id, "user", "What is an LLM?"),
        make_message(conversation.id, "assistant", "A language model.", with_usage=True),
    ]

    response = client.get(f"/api/conversations/{conversation.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(conversation.id)
    assert body["title"] == "What is an LLM?"
    assert [(m["role"], m["content"]) for m in body["messages"]] == [
        ("user", "What is an LLM?"),
        ("assistant", "A language model."),
    ]
    assert body["messages"][0]["usage"] is None
    assert body["messages"][1]["usage"]["total_tokens"] == 20


def test_get_unknown_conversation_returns_404(fake_repo: MagicMock) -> None:
    fake_repo.get_conversation.return_value = None

    response = client.get(f"/api/conversations/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Conversation not found."}


def test_get_with_invalid_id_returns_422(fake_repo: MagicMock) -> None:
    response = client.get("/api/conversations/not-a-uuid")

    assert response.status_code == 422


# --- DELETE /api/conversations/{id} -----------------------------------------------

def test_delete_conversation_returns_204(fake_repo: MagicMock) -> None:
    conversation = make_conversation()
    fake_repo.get_conversation.return_value = conversation

    response = client.delete(f"/api/conversations/{conversation.id}")

    assert response.status_code == 204
    assert response.content == b""
    fake_repo.delete_conversation.assert_called_once_with(conversation.id)


def test_delete_unknown_conversation_returns_404(fake_repo: MagicMock) -> None:
    fake_repo.get_conversation.return_value = None

    response = client.delete(f"/api/conversations/{uuid4()}")

    assert response.status_code == 404
    fake_repo.delete_conversation.assert_not_called()


# --- Database down ------------------------------------------------------------------

def test_database_failure_returns_503(fake_repo: MagicMock) -> None:
    fake_repo.list_conversations.side_effect = RepositoryError("connection refused")

    response = client.get("/api/conversations")

    assert response.status_code == 503
    assert "connection refused" not in response.text
