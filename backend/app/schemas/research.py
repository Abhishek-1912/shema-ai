"""Request/response shapes for /api/research (docs/api-contract.md v9)."""

from pydantic import BaseModel

from app.schemas.agent import AgentRequest, ToolCallOut
from app.services.llm_service import TokenUsage
from app.services.research import ResearchResult
from app.services.tool_agent import ToolCallRecord


class ResearchRequest(AgentRequest):
    """Same rules as an agent question: not empty, max 2000 characters."""


class FindingOut(BaseModel):
    sub_question: str
    answer: str
    tool_calls: list[ToolCallOut]
    steps: int


class ResearchResponse(BaseModel):
    run_id: str
    question: str
    sub_questions: list[str]
    findings: list[FindingOut]
    report: str
    steps: int
    model: str | None
    usage: TokenUsage | None

    @classmethod
    def from_result(cls, result: ResearchResult, run_id: str) -> "ResearchResponse":
        return cls(
            run_id=run_id,
            question=result.question,
            sub_questions=result.sub_questions,
            findings=[
                FindingOut(
                    sub_question=f.sub_question, answer=f.answer, steps=f.steps,
                    tool_calls=[_call(c) for c in f.tool_calls],
                )
                for f in result.findings
            ],
            report=result.report,
            steps=result.steps,
            model=result.model,
            usage=result.usage,
        )


def _call(c: ToolCallRecord) -> ToolCallOut:
    return ToolCallOut(
        name=c.name, arguments=c.arguments, result=c.result, is_error=c.is_error,
        duration_ms=round(c.duration_ms, 1), approval=c.approval,
    )
