"""Integration test: agent runs, tool-call log and claim-once in the REAL database.

Needs migrations 20261118000007_agent_runs.sql and 20261118000008_agent_sessions.sql. Run with: pytest -m integration -v
No AI calls: the results are built by hand.
"""

from uuid import uuid4

import pytest

from app.core.supabase import get_supabase_client
from app.repositories.agent_run_repository import get_agent_run_repository
from app.services.tool_agent import ToolCallRecord
from tests.agent_fakes import SEARCH, done, waiting

pytestmark = pytest.mark.integration

APPROVED = ToolCallRecord("delete_document", {"document_id": "abc"}, "ok", False, 5.0, "approved")


def test_paused_run_is_saved_claimed_once_and_logged() -> None:
    repository = get_agent_run_repository()
    db = get_supabase_client()
    run_id = repository.create("Integration test: delete it", uuid4())

    try:
        paused = waiting()
        repository.save(run_id, paused, already_logged=0, ttl_seconds=900)

        # The snapshot comes back from jsonb exactly as saved — and only ONCE.
        assert repository.claim(str(run_id)).paused == paused
        assert repository.claim(str(run_id)) is None

        repository.save(run_id, done("Deleted.", [SEARCH, APPROVED]), already_logged=1, ttl_seconds=900)

        run = db.table("agent_runs").select("*").eq("id", str(run_id)).execute().data[0]
        assert (run["status"], run["answer"], run["state"]) == ("done", "Deleted.", None)
        calls = db.table("agent_tool_calls").select("*").eq("run_id", str(run_id)).order("position").execute().data
        assert [(c["position"], c["name"], c["approval"]) for c in calls] == [
            (0, "search_documents", "auto"),
            (1, "delete_document", "approved"),
        ]
    finally:
        db.table("agent_runs").delete().eq("id", str(run_id)).execute()  # tool calls cascade


def test_expired_run_cannot_be_claimed() -> None:
    repository = get_agent_run_repository()
    db = get_supabase_client()
    run_id = repository.create("Integration test: expired", uuid4())

    try:
        repository.save(run_id, waiting(), already_logged=0, ttl_seconds=-1)  # deadline already passed

        assert repository.claim(str(run_id)) is None
    finally:
        db.table("agent_runs").delete().eq("id", str(run_id)).execute()


def test_session_history_is_finished_runs_of_that_session_oldest_first() -> None:
    repository = get_agent_run_repository()
    db = get_supabase_client()
    session, other = uuid4(), uuid4()
    ids = []
    try:
        for question, answer, sess in [
            ("Paternity leave?", "4 weeks.", session),
            ("Unrelated", "Other session.", other),
            ("And for mothers?", "16 weeks.", session),
        ]:
            run_id = repository.create(question, sess)
            ids.append(run_id)
            repository.save(run_id, done(answer), already_logged=0, ttl_seconds=900)
        paused_id = repository.create("Delete it", session)  # paused: no answer yet
        ids.append(paused_id)
        repository.save(paused_id, waiting(), already_logged=0, ttl_seconds=900)

        turns = repository.history(session, limit=6)

        assert [(t.question, t.answer) for t in turns] == [
            ("Paternity leave?", "4 weeks."),
            ("And for mothers?", "16 weeks."),
        ]
        assert [t.question for t in repository.history(session, limit=1)] == ["And for mothers?"]
    finally:
        for run_id in ids:
            db.table("agent_runs").delete().eq("id", str(run_id)).execute()
