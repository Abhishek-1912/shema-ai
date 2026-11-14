"""Repository: the ONE place that reads/writes conversations and messages in Supabase.

Like a Spring Data repository: the rest of the app calls methods such as
add_message() and never writes database queries itself.
"""

from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, Literal
from uuid import UUID

import httpx
from postgrest.exceptions import APIError
from supabase import Client

from app.core.supabase import get_supabase_client
from app.models.conversation import Conversation, StoredMessage
from app.services.llm_service import TokenUsage

CONVERSATIONS = "conversations"
MESSAGES = "messages"


class RepositoryError(Exception):
    """The database could not be reached or rejected the operation."""


class ConversationRepository:
    def __init__(self, client: Client) -> None:
        self._client = client

    # --- Conversations -------------------------------------------------------

    def create_conversation(self, title: str = "New conversation") -> Conversation:
        rows = self._run(self._client.table(CONVERSATIONS).insert({"title": title}))
        return Conversation.model_validate(rows[0])

    def get_conversation(self, conversation_id: UUID) -> Conversation | None:
        rows = self._run(
            self._client.table(CONVERSATIONS).select("*").eq("id", str(conversation_id))
        )
        return Conversation.model_validate(rows[0]) if rows else None

    def list_conversations(self, limit: int = 50) -> list[Conversation]:
        rows = self._run(
            self._client.table(CONVERSATIONS)
            .select("*")
            .order("updated_at", desc=True)
            .limit(limit)
        )
        return [Conversation.model_validate(row) for row in rows]

    def delete_conversation(self, conversation_id: UUID) -> None:
        # Messages are deleted automatically by "on delete cascade".
        self._run(self._client.table(CONVERSATIONS).delete().eq("id", str(conversation_id)))

    # --- Messages ------------------------------------------------------------

    def add_message(
        self,
        conversation_id: UUID,
        role: Literal["user", "assistant"],
        content: str,
        model: str | None = None,
        usage: TokenUsage | None = None,
    ) -> StoredMessage:
        row: dict[str, Any] = {
            "conversation_id": str(conversation_id),
            "role": role,
            "content": content,
            "model": model,
        }
        if usage is not None:
            row |= usage.model_dump()  # input_tokens, output_tokens, thinking_tokens, total_tokens

        rows = self._run(self._client.table(MESSAGES).insert(row))

        # Move this conversation to the top of the "recent chats" list.
        self._run(
            self._client.table(CONVERSATIONS)
            .update({"updated_at": datetime.now(UTC).isoformat()})
            .eq("id", str(conversation_id))
        )
        return StoredMessage.model_validate(rows[0])

    def get_messages(self, conversation_id: UUID) -> list[StoredMessage]:
        rows = self._run(
            self._client.table(MESSAGES)
            .select("*")
            .eq("conversation_id", str(conversation_id))
            .order("created_at")
        )
        return [StoredMessage.model_validate(row) for row in rows]

    # --- Helper --------------------------------------------------------------

    @staticmethod
    def _run(query: Any) -> list[dict[str, Any]]:
        """Execute a query and translate library errors into our own RepositoryError."""
        try:
            return query.execute().data
        except APIError as error:
            raise RepositoryError(f"Database rejected the request: {error.message}") from error
        except httpx.HTTPError as error:
            raise RepositoryError("Could not reach the database.") from error


@lru_cache
def get_conversation_repository() -> ConversationRepository:
    return ConversationRepository(get_supabase_client())
