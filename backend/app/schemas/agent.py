"""Request/response shapes for /api/agent (docs/api-contract.md v4)."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.services.llm_service import TokenUsage
from app.services.tool_agent import AgentResult

MAX_QUESTION_LENGTH = 2000


class AgentRequest(BaseModel):
    question: str = Field(max_length=MAX_QUESTION_LENGTH)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be empty")
        return value


class DecisionsRequest(BaseModel):
    decisions: dict[str, bool]  # call_id → approve?


class ToolCallOut(BaseModel):
    name: str
    arguments: dict[str, Any]
    result: str
    is_error: bool
    duration_ms: float
    approval: Literal["auto", "approved", "rejected"]


class PendingCallOut(BaseModel):
    call_id: str
    name: str
    arguments: dict[str, Any]
    destructive: bool


class AgentRunResponse(BaseModel):
    run_id: str | None
    status: Literal["done", "needs_approval"]
    answer: str
    tool_calls: list[ToolCallOut]
    pending: list[PendingCallOut]
    steps: int
    model: str | None
    usage: TokenUsage | None

    @classmethod
    def from_result(cls, result: AgentResult, run_id: str | None) -> "AgentRunResponse":
        return cls(
            run_id=run_id,
            status=result.status,
            answer=result.answer,
            tool_calls=[
                ToolCallOut(
                    name=c.name, arguments=c.arguments, result=c.result, is_error=c.is_error,
                    duration_ms=round(c.duration_ms, 1), approval=c.approval,
                )
                for c in result.tool_calls
            ],
            pending=[
                PendingCallOut(call_id=p.call_id, name=p.name, arguments=p.arguments, destructive=p.destructive)
                for p in result.pending
            ],
            steps=result.steps,
            model=result.model,
            usage=result.usage,
        )
