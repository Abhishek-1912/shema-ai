"""Request/response shapes for POST /api/chat. Must match docs/api-contract.md."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.services.llm_service import TokenUsage


class ChatMessageIn(BaseModel):
    """One message sent by the frontend. "system" is not allowed: only the backend sets it."""

    role: Literal["user", "assistant"]
    content: str

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be empty")
        return value


class ChatRequest(BaseModel):
    messages: list[ChatMessageIn] = Field(min_length=1)

    @model_validator(mode="after")
    def last_message_must_be_from_user(self) -> "ChatRequest":
        if self.messages[-1].role != "user":
            raise ValueError('the last message must have role "user"')
        return self


class ChatResponse(BaseModel):
    reply: str
    model: str
    usage: TokenUsage | None
