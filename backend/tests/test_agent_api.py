"""API tests for /api/agent (contract v6). The agent is a fake; runs go to a fake repository."""

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.agent_runs import AgentRunService, get_agent_run_service
from app.services.llm_service import LLMRateLimitError
from app.services.tool_agent import ToolAgent, Turn
from tests.agent_fakes import SEARCH, FakeRunRepository, done, waiting

client = TestClient(app)


@pytest.fixture
def repository() -> FakeRunRepository:
    return FakeRunRepository()


@pytest.fixture
def agent(repository: FakeRunRepository) -> Iterator[MagicMock]:
    fake = MagicMock(spec=ToolAgent)
    fake.run = AsyncMock()
    fake.resume = AsyncMock()
    app.dependency_overrides[get_agent_run_service] = lambda: AgentRunService(fake, repository)
    yield fake
    app.dependency_overrides.clear()


def test_finished_run_returns_answer_tool_calls_and_its_run_id(agent: MagicMock, repository) -> None:
    agent.run.return_value = done("Fathers get 4 weeks.", [SEARCH])

    response = client.post("/api/agent", json={"question": "Paternity leave?"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"
    assert body["run_id"] in {str(run_id) for run_id in repository.runs}  # every run is recorded
    assert body["answer"] == "Fathers get 4 weeks."
    assert body["tool_calls"] == [
        {"name": "search_documents", "arguments": {"query": "leave"}, "result": '{"result": []}',
         "is_error": False, "duration_ms": 12.3, "approval": "auto"}
    ]
    assert body["pending"] == [] and body["usage"]["total_tokens"] == 15
    assert body["session_id"]  # a new session was started
    agent.run.assert_awaited_once_with("Paternity leave?", [])


def test_paused_run_returns_a_run_id_and_pending_actions(agent: MagicMock) -> None:
    agent.run.return_value = waiting()

    body = client.post("/api/agent", json={"question": "Delete it"}).json()

    assert body["status"] == "needs_approval" and body["run_id"]
    assert body["pending"] == [
        {"call_id": "d1", "name": "delete_document", "arguments": {"document_id": "abc"}, "destructive": True}
    ]
    assert body["answer"] == ""


def test_decisions_resume_the_saved_run(agent: MagicMock) -> None:
    agent.run.return_value = waiting()
    agent.resume.return_value = done("Deleted.")
    run_id = client.post("/api/agent", json={"question": "Delete it"}).json()["run_id"]

    response = client.post(f"/api/agent/runs/{run_id}/decisions", json={"decisions": {"d1": True}})

    assert response.status_code == 200
    assert response.json()["answer"] == "Deleted." and response.json()["run_id"] == run_id
    assert response.json()["session_id"]
    agent.resume.assert_awaited_once_with(waiting(), {"d1": True})


def test_a_run_can_be_decided_only_once(agent: MagicMock) -> None:
    agent.run.return_value = waiting()
    agent.resume.return_value = done()
    run_id = client.post("/api/agent", json={"question": "Delete it"}).json()["run_id"]
    client.post(f"/api/agent/runs/{run_id}/decisions", json={"decisions": {"d1": True}})

    again = client.post(f"/api/agent/runs/{run_id}/decisions", json={"decisions": {"d1": True}})

    assert again.status_code == 404
    assert "expired or was already answered" in again.json()["detail"]
    agent.resume.assert_awaited_once()  # the action could not be triggered twice


@pytest.mark.parametrize("run_id", ["does-not-exist", "00000000-0000-0000-0000-000000000000"])
def test_unknown_run_is_404(agent: MagicMock, run_id: str) -> None:
    response = client.post(f"/api/agent/runs/{run_id}/decisions", json={"decisions": {}})

    assert response.status_code == 404


def test_a_resumed_run_can_pause_again_under_the_same_id(agent: MagicMock) -> None:
    agent.run.return_value = waiting()
    agent.resume.return_value = waiting()  # asks for another approval
    first = client.post("/api/agent", json={"question": "Two steps"}).json()["run_id"]

    second = client.post(f"/api/agent/runs/{first}/decisions", json={"decisions": {"d1": True}}).json()

    assert second["status"] == "needs_approval" and second["run_id"] == first


def test_failed_resume_is_not_retryable(agent: MagicMock, repository) -> None:
    agent.run.return_value = waiting()
    agent.resume.side_effect = LLMRateLimitError("quota")
    run_id = client.post("/api/agent", json={"question": "Delete it"}).json()["run_id"]

    response = client.post(f"/api/agent/runs/{run_id}/decisions", json={"decisions": {"d1": True}})
    retry = client.post(f"/api/agent/runs/{run_id}/decisions", json={"decisions": {"d1": True}})

    assert response.status_code == 429
    assert retry.status_code == 404  # not put back: an approved action must never run twice
    [run] = repository.runs.values()
    assert run["status"] == "failed"


@pytest.mark.parametrize("payload", [{}, {"question": "  "}, {"question": "x" * 2001}])
def test_invalid_question_is_422(agent: MagicMock, payload: dict, repository) -> None:
    assert client.post("/api/agent", json=payload).status_code == 422
    agent.run.assert_not_awaited()
    assert repository.runs == {}  # nothing recorded for a rejected request


def test_follow_up_with_session_id_remembers_the_earlier_answer(agent: MagicMock) -> None:
    agent.run.return_value = done("Fathers get 4 weeks.")
    first = client.post("/api/agent", json={"question": "Paternity leave?"}).json()
    agent.run.return_value = done("Mothers get 16 weeks.")

    second = client.post(
        "/api/agent", json={"question": "And for mothers?", "session_id": first["session_id"]}
    ).json()

    assert second["session_id"] == first["session_id"]
    assert agent.run.await_args.args[1] == [Turn("Paternity leave?", "Fathers get 4 weeks.")]


def test_invalid_session_id_is_422(agent: MagicMock) -> None:
    response = client.post("/api/agent", json={"question": "Hi", "session_id": "not-a-uuid"})

    assert response.status_code == 422


def test_response_contains_the_plan(agent: MagicMock) -> None:
    result = done("Fathers get 4 weeks.")
    result.plan = ["Search the documents for paternity leave"]
    agent.run.return_value = result

    body = client.post("/api/agent", json={"question": "Paternity leave?"}).json()

    assert body["plan"] == ["Search the documents for paternity leave"]
