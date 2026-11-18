"""Unit tests for AgentRunRepository. No real database: the Supabase client is a mock."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

from app.repositories.agent_run_repository import AgentRunRepository, ClaimedRun
from app.services.agent_snapshot import to_snapshot
from app.services.tool_agent import ToolCallRecord, Turn
from tests.agent_fakes import SEARCH, done, waiting

RUN_ID = uuid4()
SESSION_ID = uuid4()
NOW = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)


def fake_client_returning(*results: list[dict]) -> MagicMock:
    query = MagicMock()
    for method in ("select", "insert", "update", "delete", "eq", "order", "limit"):
        getattr(query, method).return_value = query
    query.execute.side_effect = [MagicMock(data=result) for result in results]
    client = MagicMock()
    client.table.return_value = query
    client.rpc.return_value = query
    client.query = query
    return client


def repo(client: MagicMock) -> AgentRunRepository:
    return AgentRunRepository(client, clock=lambda: NOW)


def test_create_inserts_a_running_row_in_its_session() -> None:
    client = fake_client_returning([{"id": str(RUN_ID)}])

    assert repo(client).create("Paternity leave?", SESSION_ID) == RUN_ID
    client.query.insert.assert_called_once_with(
        {"question": "Paternity leave?", "status": "running", "session_id": str(SESSION_ID)}
    )


def test_history_returns_finished_turns_oldest_first() -> None:
    # The database returns newest first (ORDER BY created_at DESC LIMIT n) ...
    client = fake_client_returning([
        {"question": "And for mothers?", "answer": "16 weeks."},
        {"question": "Paternity leave?", "answer": "4 weeks."},
    ])

    turns = repo(client).history(SESSION_ID, limit=6)

    # ... the agent needs them in conversation order.
    assert turns == [Turn("Paternity leave?", "4 weeks."), Turn("And for mothers?", "16 weeks.")]
    client.query.eq.assert_any_call("session_id", str(SESSION_ID))
    client.query.eq.assert_any_call("status", "done")  # no paused/failed runs in memory
    client.query.order.assert_called_once_with("created_at", desc=True)
    client.query.limit.assert_called_once_with(6)


def test_history_cuts_long_answers() -> None:
    client = fake_client_returning([{"question": "Q", "answer": "x" * 5000}])

    [turn] = repo(client).history(SESSION_ID, limit=6)

    assert len(turn.answer) < 1600 and turn.answer.endswith("[cut]")


def test_save_finished_run_logs_calls_and_clears_state() -> None:
    client = fake_client_returning([], [])

    repo(client).save(RUN_ID, done("4 weeks.", [SEARCH]), already_logged=0, ttl_seconds=900)

    [logged] = client.query.insert.call_args.args[0]
    assert logged == {
        "run_id": str(RUN_ID), "position": 0, "name": "search_documents", "arguments": {"query": "leave"},
        "result": '{"result": []}', "is_error": False, "duration_ms": 12.345, "approval": "auto",
    }
    update = client.query.update.call_args.args[0]
    assert update["status"] == "done" and update["answer"] == "4 weeks."
    assert update["state"] is None and update["expires_at"] is None
    assert update["usage"]["total_tokens"] == 15
    client.query.eq.assert_called_with("id", str(RUN_ID))


def test_save_paused_run_stores_snapshot_and_deadline() -> None:
    client = fake_client_returning([], [])
    paused = waiting()

    repo(client).save(RUN_ID, paused, already_logged=0, ttl_seconds=900)

    update = client.query.update.call_args.args[0]
    assert update["status"] == "needs_approval"
    assert update["state"] == to_snapshot(paused)
    assert update["expires_at"] == "2026-11-18T12:15:00+00:00"


def test_save_after_resume_logs_only_new_calls_at_the_right_positions() -> None:
    client = fake_client_returning([], [])
    approved = ToolCallRecord("delete_document", {"document_id": "abc"}, "ok", False, 5.0, "approved")

    repo(client).save(RUN_ID, done("Deleted.", [SEARCH, approved]), already_logged=1, ttl_seconds=900)

    [logged] = client.query.insert.call_args.args[0]
    assert logged["position"] == 1 and logged["approval"] == "approved"


def test_save_without_new_calls_inserts_nothing() -> None:
    client = fake_client_returning([])

    repo(client).save(RUN_ID, done(), already_logged=0, ttl_seconds=900)

    client.query.insert.assert_not_called()


def test_claim_returns_the_restored_run_and_its_session() -> None:
    paused = waiting()
    client = fake_client_returning([{"id": str(RUN_ID), "state": to_snapshot(paused), "session_id": str(SESSION_ID)}])

    assert repo(client).claim(str(RUN_ID)) == ClaimedRun(paused, SESSION_ID)
    client.rpc.assert_called_once_with("claim_agent_run", {"p_id": str(RUN_ID)})


def test_claim_of_unknown_expired_or_decided_run_is_none() -> None:
    client = fake_client_returning([])  # the SQL function returned no row

    assert repo(client).claim(str(RUN_ID)) is None


def test_claim_with_an_invalid_id_does_not_call_the_database() -> None:
    client = fake_client_returning()

    assert repo(client).claim("not-a-uuid") is None
    client.rpc.assert_not_called()


def test_mark_failed_drops_state_and_cuts_long_errors() -> None:
    client = fake_client_returning([])

    repo(client).mark_failed(RUN_ID, "x" * 5000)

    update = client.query.update.call_args.args[0]
    assert update["status"] == "failed" and update["state"] is None
    assert len(update["error"]) == 2000


def test_save_stores_the_plan() -> None:
    client = fake_client_returning([])
    result = done()
    result.plan = ["Search the documents"]

    repo(client).save(RUN_ID, result, already_logged=0, ttl_seconds=900)

    assert client.query.update.call_args.args[0]["plan"] == ["Search the documents"]
