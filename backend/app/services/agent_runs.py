"""Runs the agent and records every run in the database.

    start(question)        → new row "running" → agent.run() → saved (done / needs_approval)
    decide(run_id, ...)    → claim the paused run (once!) → agent.resume() → saved
    any crash              → row marked "failed" with the error, never retried

Paused runs live in the database (not in memory), so they survive a backend restart
and work with several backend processes. Claiming is atomic in SQL: an approved
action can never run twice, even if two decision requests arrive together.
"""

import asyncio
from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID, uuid4

from app.repositories.agent_run_repository import AgentRunRepository, get_agent_run_repository
from app.services.tool_agent import AgentResult, ToolAgent, get_tool_agent

DEFAULT_TTL_SECONDS = 15 * 60  # how long a paused run waits for a decision
DEFAULT_MEMORY_TURNS = 6  # earlier Q&A pairs of the session the agent sees


class RunNotFoundError(Exception):
    """No paused run with this id (unknown, expired or already decided)."""

    def __init__(self, run_id: str) -> None:
        super().__init__(f"Agent run {run_id} not found or expired.")
        self.run_id = run_id


@dataclass(frozen=True)
class RecordedRun:
    run_id: UUID
    session_id: UUID | None  # None only for a paused run saved before sessions existed
    result: AgentResult


class AgentRunService:
    def __init__(
        self,
        agent: ToolAgent,
        repository: AgentRunRepository,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        memory_turns: int = DEFAULT_MEMORY_TURNS,
    ) -> None:
        self._agent = agent
        self._repository = repository
        self._ttl = ttl_seconds
        self._memory_turns = memory_turns

    async def start(self, question: str, session_id: UUID | None = None) -> RecordedRun:
        """Run a question. Same `session_id` as earlier runs = the agent remembers them;
        None = start a new session.
        """
        session_id = session_id or uuid4()
        # The repository is synchronous (Supabase REST client): run it in a worker
        # thread so the event loop keeps serving other requests meanwhile.
        history = await asyncio.to_thread(self._repository.history, session_id, self._memory_turns)
        run_id = await asyncio.to_thread(self._repository.create, question.strip(), session_id)
        result = await self._guarded(run_id, self._agent.run(question, history))
        await asyncio.to_thread(self._repository.save, run_id, result, 0, self._ttl)
        return RecordedRun(run_id, session_id, result)

    async def decide(self, run_id: str, decisions: dict[str, bool]) -> RecordedRun:
        claimed = await asyncio.to_thread(self._repository.claim, run_id)
        if claimed is None:
            raise RunNotFoundError(run_id)
        uuid = UUID(run_id)
        # If resuming fails, the run is marked failed and NOT put back: an approved
        # action may already have run, and retrying could do it twice.
        result = await self._guarded(uuid, self._agent.resume(claimed.paused, decisions))
        await asyncio.to_thread(self._repository.save, uuid, result, len(claimed.paused.tool_calls), self._ttl)
        return RecordedRun(uuid, claimed.session_id, result)

    async def _guarded(self, run_id: UUID, work) -> AgentResult:
        try:
            return await work
        except Exception as error:
            await asyncio.to_thread(self._repository.mark_failed, run_id, f"{type(error).__name__}: {error}")
            raise


@lru_cache
def get_agent_run_service() -> AgentRunService:
    return AgentRunService(get_tool_agent(), get_agent_run_repository())
