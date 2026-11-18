"""Shared fakes for agent-run tests: example results and an in-memory repository."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.repositories.agent_run_repository import ClaimedRun
from app.services.agent_snapshot import from_snapshot, to_snapshot
from app.services.llm_service import TokenUsage
from app.services.tool_agent import AgentResult, AgentState, PendingToolCall, ToolCallRecord, Turn, _StepItem

SEARCH = ToolCallRecord("search_documents", {"query": "leave"}, '{"result": []}', False, 12.345)
DELETE = PendingToolCall("d1", "delete_document", {"document_id": "abc"}, destructive=True)
USAGE = TokenUsage(input_tokens=10, output_tokens=5, thinking_tokens=0, total_tokens=15)


def done(answer: str = "Done.", calls: list[ToolCallRecord] | None = None) -> AgentResult:
    return AgentResult(answer=answer, tool_calls=calls or [], steps=2, model="fake-model", usage=USAGE)


def waiting(calls: list[ToolCallRecord] | None = None) -> AgentResult:
    """A paused run with a real saved state, like ToolAgent produces."""
    state = AgentState(
        messages=[
            {"role": "system", "content": "You are Shema AI."},
            {"role": "user", "content": "Delete it"},
            {
                "role": "assistant",
                "tool_calls": [
                    {"id": "s1", "type": "function", "function": {"name": "search_documents", "arguments": "{}"},
                     "extra_content": {"google": {"thought_signature": "sig=="}}},
                    {"id": "d1", "type": "function",
                     "function": {"name": "delete_document", "arguments": '{"document_id": "abc"}'}},
                ],
            },
        ],
        steps_left=4,
        step_items=[
            _StepItem("s1", "search_documents", {"query": "leave"}, SEARCH),
            _StepItem("d1", "delete_document", {"document_id": "abc"}, None),
        ],
        pending=[DELETE],
    )
    return AgentResult(
        status="needs_approval", tool_calls=list(calls if calls is not None else [SEARCH]), pending=[DELETE],
        state=state, steps=1, model="fake-model", usage=USAGE,
    )


class FakeRunRepository:
    """Behaves like AgentRunRepository (incl. claim-once and expiry), without a database."""

    def __init__(self) -> None:
        self.now = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)
        self.runs: dict[UUID, dict] = {}
        self.tool_calls: dict[UUID, list[ToolCallRecord]] = {}

    def create(self, question: str, session_id: UUID) -> UUID:
        run_id = uuid4()
        self.runs[run_id] = {
            "question": question, "status": "running", "state": None, "expires_at": None,
            "session_id": session_id, "answer": "",
        }
        self.tool_calls[run_id] = []
        return run_id

    def history(self, session_id: UUID, limit: int) -> list[Turn]:
        done_runs = [r for r in self.runs.values() if r["session_id"] == session_id and r["status"] == "done"]
        return [Turn(r["question"], r["answer"]) for r in done_runs[-limit:]]  # dicts keep insertion order

    def save(self, run_id: UUID, result: AgentResult, already_logged: int, ttl_seconds: float) -> None:
        assert len(self.tool_calls[run_id]) == already_logged, "tool calls logged twice or skipped"
        self.tool_calls[run_id].extend(result.tool_calls[already_logged:])
        paused = result.status == "needs_approval"
        self.runs[run_id].update(
            status=result.status,
            answer=result.answer,
            state=to_snapshot(result) if paused else None,
            expires_at=self.now + timedelta(seconds=ttl_seconds) if paused else None,
        )

    def claim(self, run_id: str) -> ClaimedRun | None:
        try:
            run = self.runs.get(UUID(run_id))
        except ValueError:
            return None
        if run is None or run["status"] != "needs_approval" or run["expires_at"] <= self.now:
            return None
        run["status"] = "resuming"
        return ClaimedRun(from_snapshot(run["state"]), run["session_id"])

    def mark_failed(self, run_id: UUID, error: str) -> None:
        self.runs[run_id].update(status="failed", error=error, state=None, expires_at=None)
