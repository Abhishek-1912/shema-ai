"""The `Message` shape shared by several endpoints (docs/api-contract.md)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.models.conversation import StoredMessage
from app.services.llm_service import TokenUsage


class MessageOut(BaseModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    model: str | None
    usage: TokenUsage | None

    @classmethod
    def from_stored(cls, message: StoredMessage) -> "MessageOut":
        """Database row (flat token columns) → API shape (nested `usage` object)."""
        tokens = (
            message.input_tokens,
            message.output_tokens,
            message.thinking_tokens,
            message.total_tokens,
        )
        usage = None
        if all(value is not None for value in tokens):
            usage = TokenUsage(
                input_tokens=message.input_tokens,
                output_tokens=message.output_tokens,
                thinking_tokens=message.thinking_tokens,
                total_tokens=message.total_tokens,
            )
        return cls(
            id=message.id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
            model=message.model,
            usage=usage,
        )
