"""Integration test: talks to your REAL Supabase project.

Skipped by default. Run it explicitly with:
    pytest -m integration -v

It creates a test conversation, adds messages, reads them back, then deletes everything.
"""

import pytest

from app.repositories.conversation_repository import get_conversation_repository
from app.services.llm_service import TokenUsage

pytestmark = pytest.mark.integration


def test_full_conversation_round_trip() -> None:
    repo = get_conversation_repository()
    conversation = repo.create_conversation("Integration test (safe to delete)")

    try:
        repo.add_message(conversation.id, "user", "What is an LLM?")
        repo.add_message(
            conversation.id,
            "assistant",
            "An LLM is a large language model.",
            model="test-model",
            usage=TokenUsage(input_tokens=10, output_tokens=8, thinking_tokens=0, total_tokens=18),
        )

        messages = repo.get_messages(conversation.id)
        assert [(m.role, m.content) for m in messages] == [
            ("user", "What is an LLM?"),
            ("assistant", "An LLM is a large language model."),
        ]
        assert messages[1].total_tokens == 18

        listed_ids = [c.id for c in repo.list_conversations()]
        assert conversation.id in listed_ids
    finally:
        repo.delete_conversation(conversation.id)

    # Cascade delete removed the messages too.
    assert repo.get_conversation(conversation.id) is None
    assert repo.get_messages(conversation.id) == []
