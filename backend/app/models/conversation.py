"""Data as it is stored in the database (one class per table row)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class Conversation(BaseModel):
    id: UUID
    user_id: UUID | None = None
    title: str
    created_at: datetime
    updated_at: datetime


class StoredMessage(BaseModel):
    id: UUID
    conversation_id: UUID
    role: Literal["user", "assistant"]
    content: str
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    thinking_tokens: int | None = None
    total_tokens: int | None = None
    created_at: datetime
