"""Small helpers that build fake domain objects for tests."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.models.conversation import Conversation, StoredMessage

NOW = datetime(2026, 11, 15, 10, 0, tzinfo=UTC)


def make_conversation(conversation_id: UUID | None = None, title: str = "What is an LLM?") -> Conversation:
    return Conversation(
        id=conversation_id or uuid4(),
        title=title,
        created_at=NOW,
        updated_at=NOW,
    )


def make_message(
    conversation_id: UUID,
    role: str = "user",
    content: str = "Hi",
    with_usage: bool = False,
) -> StoredMessage:
    extra = {}
    if with_usage:
        extra = {
            "model": "fake-model",
            "input_tokens": 10,
            "output_tokens": 6,
            "thinking_tokens": 4,
            "total_tokens": 20,
        }
    return StoredMessage(
        id=uuid4(),
        conversation_id=conversation_id,
        role=role,
        content=content,
        created_at=NOW,
        **extra,
    )
