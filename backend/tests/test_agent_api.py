"""API tests for /api/agent (contract v4). The agent is a fake; the run store is real."""

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.llm_service import LLMRateLimitError, TokenUsage
from app.services.pending_runs import PendingRunStore, get_pending_runs
from app.services.tool_agent import AgentResult, PendingToolCall, ToolAgent, ToolCallRecord, get_tool_agent

client = TestClient(app)

SEARCH = ToolCallRecord("search_documents", {"query": "leave"}, '{"result": []}', False, 12.345)
DELETE = PendingToolCall("d1", "delete_document", {"document_id": "abc"}, destructive=True)


def done(answer: str = "Done.", calls: list[ToolCallRecord] | None = None) -> AgentResult:
    return AgentResult(
        answer=answer, tool_calls=calls or [], steps=2, model="fake-model",
        usage=TokenUsage(input_tokens=10, output_tokens=5, thinking_tokens=0, total_tokens=15),
    )


def waiting() -> AgentResult:
    return AgentResult(status="needs_approval", tool_calls=[SEARCH], pending=[DELETE], steps=1, model="fake-model")


@pytest.fixture
def store() -> PendingRunStore:
    return PendingRunStore()


@pytest.fixture
def agent(store: PendingRunStore) -> Iterator[MagicMock]:
    fake = MagicMock(spec=ToolAgent)
    fake.run = AsyncMock()
    fake.resume = AsyncMock()
    app.dependency_overrides[get_tool_agent] = lambda: fake
    app.dependency_overrides[get_pending_runs] = lambda: store
    yield fake
    app.dependency_overrides.clear()


def test_finished_run_returns_answer_and_tool_calls(agent: MagicMock) -> None:
    agent.run.return_value = done("Fathers get 4 weeks.", [SEARCH])

    response = client.post("/api/agent", json={"question": "Paternity leave?"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done" and body["run_id"] is None
    assert body["answer"] == "Fathers get 4 weeks."
    assert body["tool_calls"] == [
        {"name": "search_documents", "arguments": {"query": "leave"}, "result": '{"result": []}',
         "is_error": False, "duration_ms": 12.3, "approval": "auto"}
    ]
    assert body["pending"] == [] and body["usage"]["total_tokens"] == 15
    agent.run.assert_awaited_once_with("Paternity leave?")


def test_paused_run_returns_a_run_id_and_pending_actions(agent: MagicMock, store: PendingRunStore) -> None:
    agent.run.return_value = waiting()

    body = client.post("/api/agent", json={"question": "Delete it"}).json()

    assert body["status"] == "needs_approval"
    assert body["run_id"] and len(store) == 1
    assert body["pending"] == [
        {"call_id": "d1", "name": "delete_document", "arguments": {"document_id": "abc"}, "destructive": True}
    ]
    assert body["answer"] == ""


def test_decisions_resume_the_stored_run(agent: MagicMock, store: PendingRunStore) -> None:
    paused = waiting()
    agent.run.return_value = paused
    agent.resume.return_value = done("Deleted.")
    run_id = client.post("/api/agent", json={"question": "Delete it"}).json()["run_id"]

    response = client.post(f"/api/agent/runs/{run_id}/decisions", json={"decisions": {"d1": True}})

    assert response.status_code == 200
    assert response.json()["answer"] == "Deleted."
    agent.resume.assert_awaited_once_with(paused, {"d1": True})
    assert len(store) == 0


def test_a_run_can_be_decided_only_once(agent: MagicMock) -> None:
    agent.run.return_value = waiting()
    agent.resume.return_value = done()
    run_id = client.post("/api/agent", json={"question": "Delete it"}).json()["run_id"]
    client.post(f"/api/agent/runs/{run_id}/decisions", json={"decisions": {"d1": True}})

    again = client.post(f"/api/agent/runs/{run_id}/decisions", json={"decisions": {"d1": True}})

    assert again.status_code == 404
    assert "expired or was already answered" in again.json()["detail"]
    agent.resume.assert_awaited_once()  # the action could not be triggered twice


def test_unknown_run_is_404(agent: MagicMock) -> None:
    response = client.post("/api/agent/runs/does-not-exist/decisions", json={"decisions": {}})

    assert response.status_code == 404


def test_a_resumed_run_can_pause_again(agent: MagicMock, store: PendingRunStore) -> None:
    agent.run.return_value = waiting()
    agent.resume.return_value = waiting()  # asks for another approval
    first = client.post("/api/agent", json={"question": "Two steps"}).json()["run_id"]

    second = client.post(f"/api/agent/runs/{first}/decisions", json={"decisions": {"d1": True}}).json()

    assert second["status"] == "needs_approval"
    assert second["run_id"] and second["run_id"] != first


def test_failed_resume_is_not_retryable(agent: MagicMock, store: PendingRunStore) -> None:
    agent.run.return_value = waiting()
    agent.resume.side_effect = LLMRateLimitError("quota")
    run_id = client.post("/api/agent", json={"question": "Delete it"}).json()["run_id"]

    response = client.post(f"/api/agent/runs/{run_id}/decisions", json={"decisions": {"d1": True}})

    assert response.status_code == 429
    assert len(store) == 0  # not put back: an approved action must never run twice


@pytest.mark.parametrize("payload", [{}, {"question": "  "}, {"question": "x" * 2001}])
def test_invalid_question_is_422(agent: MagicMock, payload: dict) -> None:
    assert client.post("/api/agent", json=payload).status_code == 422
    agent.run.assert_not_awaited()
