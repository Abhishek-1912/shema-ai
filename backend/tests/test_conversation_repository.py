"""Unit tests for ConversationRepository. No real database: the Supabase client is a mock."""

from unittest.mock import MagicMock
from uuid import uuid4

import httpx
import pytest
from postgrest.exceptions import APIError

from app.repositories.conversation_repository import ConversationRepository, RepositoryError
from app.services.llm_service import TokenUsage

CONVERSATION_ID = uuid4()
NOW = "2026-11-15T10:00:00+00:00"


def conversation_row(title: str = "New conversation") -> dict:
    return {
        "id": str(CONVERSATION_ID),
        "user_id": None,
        "title": title,
        "created_at": NOW,
        "updated_at": NOW,
    }


def message_row(role: str = "user", content: str = "Hi", **extra: object) -> dict:
    return {
        "id": str(uuid4()),
        "conversation_id": str(CONVERSATION_ID),
        "role": role,
        "content": content,
        "model": None,
        "input_tokens": None,
        "output_tokens": None,
        "thinking_tokens": None,
        "total_tokens": None,
        "created_at": NOW,
        **extra,
    }


def fake_client_returning(*results: list[dict]) -> MagicMock:
    """A fake Supabase client. Each .execute() call returns the next result, in order.

    Supabase queries are chains (client.table(...).select(...).eq(...).execute()).
    Every chain method returns the same `query` mock, so any chain ends at our execute().
    """
    query = MagicMock()
    for method in ("select", "insert", "update", "delete", "eq", "order", "limit"):
        getattr(query, method).return_value = query
    query.execute.side_effect = [MagicMock(data=result) for result in results]

    client = MagicMock()
    client.table.return_value = query
    client.query = query  # so tests can inspect what was called
    return client


# --- Reading and writing ------------------------------------------------------

def test_create_conversation_returns_model() -> None:
    client = fake_client_returning([conversation_row("My chat")])

    conversation = ConversationRepository(client).create_conversation("My chat")

    assert conversation.id == CONVERSATION_ID
    assert conversation.title == "My chat"
    client.table.assert_called_with("conversations")
    client.query.insert.assert_called_once_with({"title": "My chat"})


def test_get_conversation_returns_none_when_missing() -> None:
    client = fake_client_returning([])

    assert ConversationRepository(client).get_conversation(CONVERSATION_ID) is None


def test_list_conversations_newest_first() -> None:
    client = fake_client_returning([conversation_row("B"), conversation_row("A")])

    conversations = ConversationRepository(client).list_conversations(limit=10)

    assert [c.title for c in conversations] == ["B", "A"]
    client.query.order.assert_called_once_with("updated_at", desc=True)
    client.query.limit.assert_called_once_with(10)


def test_add_assistant_message_saves_model_and_usage() -> None:
    saved = message_row("assistant", "Hello!", model="fake-model", total_tokens=20)
    client = fake_client_returning([saved], [conversation_row()])  # insert, then update

    message = ConversationRepository(client).add_message(
        CONVERSATION_ID,
        "assistant",
        "Hello!",
        model="fake-model",
        usage=TokenUsage(input_tokens=10, output_tokens=6, thinking_tokens=4, total_tokens=20),
    )

    assert message.role == "assistant"
    assert message.total_tokens == 20
    client.query.insert.assert_called_once_with(
        {
            "conversation_id": str(CONVERSATION_ID),
            "role": "assistant",
            "content": "Hello!",
            "model": "fake-model",
            "input_tokens": 10,
            "output_tokens": 6,
            "thinking_tokens": 4,
            "total_tokens": 20,
        }
    )
    # The conversation's updated_at is bumped so it moves to the top of the list.
    assert "updated_at" in client.query.update.call_args.args[0]


def test_get_messages_in_order() -> None:
    client = fake_client_returning([message_row("user", "Hi"), message_row("assistant", "Hello")])

    messages = ConversationRepository(client).get_messages(CONVERSATION_ID)

    assert [(m.role, m.content) for m in messages] == [("user", "Hi"), ("assistant", "Hello")]
    client.query.order.assert_called_once_with("created_at")


# --- Error translation ----------------------------------------------------------

def test_database_rejection_becomes_repository_error() -> None:
    client = fake_client_returning()
    client.query.execute.side_effect = APIError(
        {"message": "violates check constraint", "code": "23514", "hint": None, "details": None}
    )

    with pytest.raises(RepositoryError, match="violates check constraint"):
        ConversationRepository(client).create_conversation()


def test_network_failure_becomes_repository_error() -> None:
    client = fake_client_returning()
    client.query.execute.side_effect = httpx.ConnectError("no internet")

    with pytest.raises(RepositoryError, match="Could not reach"):
        ConversationRepository(client).list_conversations()
