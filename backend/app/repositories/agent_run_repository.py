"""Repository for agent runs and their tool-call log (tables agent_runs, agent_tool_calls)."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from uuid import UUID

from supabase import Client

from app.core.supabase import get_supabase_client
from app.repositories.base import execute_query
from app.services.agent_snapshot import from_snapshot, to_snapshot
from app.services.tool_agent import AgentResult, Turn

RUNS = "agent_runs"
TOOL_CALLS = "agent_tool_calls"
MAX_ERROR_CHARS = 2000
MAX_REMEMBERED_ANSWER_CHARS = 1500  # long earlier answers are cut so memory stays cheap


def _shorten(answer: str) -> str:
    if len(answer) <= MAX_REMEMBERED_ANSWER_CHARS:
        return answer
    return answer[:MAX_REMEMBERED_ANSWER_CHARS] + " …[cut]"


@dataclass(frozen=True)
class ClaimedRun:
    paused: AgentResult
    session_id: UUID | None  # None only for runs saved before sessions existed


class AgentRunRepository:
    def __init__(self, client: Client, clock=lambda: datetime.now(UTC)) -> None:
        self._client = client
        self._clock = clock

    _run = staticmethod(execute_query)

    def create(self, question: str, session_id: UUID) -> UUID:
        """Record a new run (status "running") before the agent starts."""
        rows = self._run(
            self._client.table(RUNS).insert(
                {"question": question, "status": "running", "session_id": str(session_id)}
            )
        )
        return UUID(rows[0]["id"])

    def history(self, session_id: UUID, limit: int) -> list[Turn]:
        """The last `limit` FINISHED runs of a session, oldest first (the agent's memory).

        Paused, failed or still running runs have no final answer, so they are left out.
        """
        rows = self._run(
            self._client.table(RUNS)
            .select("question, answer")
            .eq("session_id", str(session_id))
            .eq("status", "done")
            .order("created_at", desc=True)
            .limit(limit)
        )
        return [
            Turn(row["question"], _shorten(row["answer"])) for row in reversed(rows)
        ]

    def save(self, run_id: UUID, result: AgentResult, already_logged: int, ttl_seconds: float) -> None:
        """Store the outcome of run()/resume().

        Tool calls from position `already_logged` on are new and get appended to the log.
        A paused run also stores its snapshot and an approval deadline.
        """
        new_calls = result.tool_calls[already_logged:]
        if new_calls:
            self._run(
                self._client.table(TOOL_CALLS).insert(
                    [
                        {
                            "run_id": str(run_id), "position": already_logged + i, "name": c.name,
                            "arguments": c.arguments, "result": c.result, "is_error": c.is_error,
                            "duration_ms": c.duration_ms, "approval": c.approval,
                        }
                        for i, c in enumerate(new_calls)
                    ]
                )
            )

        paused = result.status == "needs_approval"
        now = self._clock()
        self._run(
            self._client.table(RUNS)
            .update(
                {
                    "status": result.status,
                    "answer": result.answer,
                    "state": to_snapshot(result) if paused else None,
                    "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat() if paused else None,
                    "steps": result.steps,
                    "stopped_early": result.stopped_early,
                    "plan": result.plan,
                    "model": result.model,
                    "usage": result.usage.model_dump() if result.usage else None,
                    "updated_at": now.isoformat(),
                }
            )
            .eq("id", str(run_id))
        )

    def claim(self, run_id: str) -> ClaimedRun | None:
        """Take a paused run for resuming. Only ONE caller can ever get it (atomic in SQL).

        None = unknown id, expired, or already decided.
        """
        try:
            UUID(run_id)
        except ValueError:
            return None  # not even a valid id: don't bother the database
        rows = self._run(self._client.rpc("claim_agent_run", {"p_id": run_id}))
        if not rows or rows[0].get("state") is None:
            return None
        session_id = rows[0].get("session_id")
        return ClaimedRun(from_snapshot(rows[0]["state"]), UUID(session_id) if session_id else None)

    def mark_failed(self, run_id: UUID, error: str) -> None:
        """The run crashed (AI or tool error). The saved state is dropped: never retried."""
        self._run(
            self._client.table(RUNS)
            .update(
                {
                    "status": "failed", "error": error[:MAX_ERROR_CHARS], "state": None,
                    "expires_at": None, "updated_at": self._clock().isoformat(),
                }
            )
            .eq("id", str(run_id))
        )


@lru_cache
def get_agent_run_repository() -> AgentRunRepository:
    return AgentRunRepository(get_supabase_client())
