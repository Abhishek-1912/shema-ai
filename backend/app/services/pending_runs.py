"""Keeps agent runs that are waiting for a human decision, for a limited time.

When the agent pauses for approval, the HTTP request must end (the user may take
minutes to decide). The paused run is stored here under a random id; the decision
request takes it back out (once) and resumes it.

Kept in memory: simple, but lost on restart and not shared between server processes.
That's fine for one backend process; a database table would be needed to scale out.
"""

import secrets
import time
from functools import lru_cache
from threading import Lock

from app.services.tool_agent import AgentResult

DEFAULT_TTL_SECONDS = 15 * 60


class RunNotFoundError(Exception):
    """No paused run with this id (unknown, expired or already decided)."""

    def __init__(self, run_id: str) -> None:
        super().__init__(f"Agent run {run_id} not found or expired.")
        self.run_id = run_id


class PendingRunStore:
    def __init__(self, ttl_seconds: float = DEFAULT_TTL_SECONDS, clock=time.monotonic) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._runs: dict[str, tuple[float, AgentResult]] = {}
        self._lock = Lock()  # requests can arrive at the same time

    def put(self, run: AgentResult, run_id: str | None = None) -> str:
        """Store a paused run; returns its id. Ids are random and unguessable."""
        run_id = run_id or secrets.token_urlsafe(16)
        with self._lock:
            self._remove_expired()
            self._runs[run_id] = (self._clock() + self._ttl, run)
        return run_id

    def take(self, run_id: str) -> AgentResult:
        """Remove and return the run. A run can be decided only ONCE."""
        with self._lock:
            self._remove_expired()
            entry = self._runs.pop(run_id, None)
        if entry is None:
            raise RunNotFoundError(run_id)
        return entry[1]

    def __len__(self) -> int:
        with self._lock:
            self._remove_expired()
            return len(self._runs)

    def _remove_expired(self) -> None:
        now = self._clock()
        for run_id in [rid for rid, (expires, _) in self._runs.items() if expires <= now]:
            del self._runs[run_id]


@lru_cache
def get_pending_runs() -> PendingRunStore:
    return PendingRunStore()
