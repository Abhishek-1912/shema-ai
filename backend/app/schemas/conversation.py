"""Response shapes for /api/conversations endpoints (docs/api-contract.md)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.conversation import Conversation
from app.schemas.message import MessageOut


class ConversationSummary(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, conversation: Conversation) -> "ConversationSummary":
        return cls(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]


class ConversationDetail(ConversationSummary):
    messages: list[MessageOut]
