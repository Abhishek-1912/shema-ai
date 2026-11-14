"""Request/response shapes for POST /api/chat. Must match docs/api-contract.md (v2)."""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.message import MessageOut

MAX_MESSAGE_LENGTH = 8000


class ChatRequest(BaseModel):
    conversation_id: UUID | None = None  # None/omitted = start a new conversation
    message: str = Field(max_length=MAX_MESSAGE_LENGTH)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be empty")
        return value


class ChatResponse(BaseModel):
    conversation_id: UUID
    user_message: MessageOut
    assistant_message: MessageOut
