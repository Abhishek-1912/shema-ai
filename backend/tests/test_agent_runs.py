"""Unit tests for AgentRunService: every run is recorded; paused runs are decided only once."""

from datetime import timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.agent_runs import AgentRunService, RunNotFoundError
from app.services.llm_service import LLMRateLimitError
from app.services.tool_agent import ToolAgent, ToolCallRecord, Turn
from tests.agent_fakes import SEARCH, FakeRunRepository, done, waiting

APPROVED = ToolCallRecord("delete_document", {"document_id": "abc"}, "ok", False, 5.0, "approved")

pytestmark = pytest.mark.anyio  # run the async tests (anyio's pytest plugin)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def repository() -> FakeRunRepository:
    return FakeRunRepository()


@pytest.fixture
def agent() -> MagicMock:
    fake = MagicMock(spec=ToolAgent)
    fake.run = AsyncMock()
    fake.resume = AsyncMock()
    return fake


@pytest.fixture
def service(agent: MagicMock, repository: FakeRunRepository) -> AgentRunService:
    return AgentRunService(agent, repository, ttl_seconds=900)


async def test_finished_run_is_recorded_with_its_tool_calls(service, agent, repository) -> None:
    agent.run.return_value = done("4 weeks.", [SEARCH])

    recorded = await service.start("  Paternity leave?  ")

    run = repository.runs[recorded.run_id]
    assert run["question"] == "Paternity leave?"
    assert run["status"] == "done" and run["answer"] == "4 weeks."
    assert repository.tool_calls[recorded.run_id] == [SEARCH]


async def test_paused_run_survives_and_resumes_from_the_database(service, agent, repository) -> None:
    agent.run.return_value = waiting()
    agent.resume.return_value = done("Deleted.", [SEARCH, APPROVED])
    first = await service.start("Delete it")

    second = await service.decide(str(first.run_id), {"d1": True})

    assert second.run_id == first.run_id  # same run, from question to answer
    assert second.session_id == first.session_id
    resumed_from, decisions = agent.resume.await_args.args
    assert resumed_from == waiting()  # restored from the saved snapshot, not from memory
    assert decisions == {"d1": True}
    assert repository.runs[first.run_id]["status"] == "done"
    assert repository.tool_calls[first.run_id] == [SEARCH, APPROVED]  # each logged once


async def test_a_run_can_be_decided_only_once(service, agent) -> None:
    agent.run.return_value = waiting()
    agent.resume.return_value = done()
    run_id = str((await service.start("Delete it")).run_id)
    await service.decide(run_id, {"d1": True})

    with pytest.raises(RunNotFoundError):
        await service.decide(run_id, {"d1": True})
    agent.resume.assert_awaited_once()


async def test_a_resumed_run_can_pause_again(service, agent, repository) -> None:
    agent.run.return_value = waiting()
    agent.resume.return_value = waiting([SEARCH, APPROVED])
    run_id = str((await service.start("Two steps")).run_id)

    again = await service.decide(run_id, {"d1": True})

    assert again.result.status == "needs_approval"
    assert repository.runs[again.run_id]["status"] == "needs_approval"
    agent.resume.return_value = done()
    await service.decide(run_id, {"d1": True})  # the second pause can be decided too


async def test_expired_run_is_not_found(service, agent, repository) -> None:
    agent.run.return_value = waiting()
    run_id = str((await service.start("Delete it")).run_id)

    repository.now += timedelta(seconds=901)

    with pytest.raises(RunNotFoundError):
        await service.decide(run_id, {"d1": True})


@pytest.mark.parametrize("run_id", ["nope", "00000000-0000-0000-0000-000000000000"])
async def test_unknown_run_is_not_found(service, run_id: str) -> None:
    with pytest.raises(RunNotFoundError):
        await service.decide(run_id, {})


async def test_crash_during_run_is_recorded_as_failed(service, agent, repository) -> None:
    agent.run.side_effect = LLMRateLimitError("quota")

    with pytest.raises(LLMRateLimitError):
        await service.start("Anything")

    [run] = repository.runs.values()
    assert run["status"] == "failed" and "LLMRateLimitError" in run["error"]


async def test_failed_resume_is_not_retryable(service, agent, repository) -> None:
    agent.run.return_value = waiting()
    agent.resume.side_effect = LLMRateLimitError("quota")
    run_id = str((await service.start("Delete it")).run_id)

    with pytest.raises(LLMRateLimitError):
        await service.decide(run_id, {"d1": True})

    with pytest.raises(RunNotFoundError):  # never put back: an approved action must not run twice
        await service.decide(run_id, {"d1": True})
    assert repository.runs[next(iter(repository.runs))]["status"] == "failed"


# --- Memory (sessions) ------------------------------------------------------------

async def test_a_new_session_starts_without_memory(service, agent) -> None:
    agent.run.return_value = done("4 weeks.")

    recorded = await service.start("Paternity leave?")

    assert recorded.session_id is not None
    agent.run.assert_awaited_once_with("Paternity leave?", [])


async def test_follow_up_in_the_same_session_sees_earlier_answers(service, agent) -> None:
    agent.run.return_value = done("4 weeks.")
    first = await service.start("Paternity leave?")
    agent.run.return_value = done("16 weeks.")

    second = await service.start("And for mothers?", first.session_id)

    assert second.session_id == first.session_id
    question, history = agent.run.await_args.args
    assert question == "And for mothers?"
    assert history == [Turn("Paternity leave?", "4 weeks.")]


async def test_other_sessions_are_not_remembered(service, agent) -> None:
    agent.run.return_value = done("4 weeks.")
    await service.start("Paternity leave?")

    await service.start("And for mothers?", uuid4())  # a different session

    assert agent.run.await_args.args[1] == []


async def test_only_finished_runs_are_remembered(service, agent) -> None:
    agent.run.return_value = waiting()  # still waiting for approval: no answer yet
    paused = await service.start("Delete it")
    agent.run.return_value = done()

    await service.start("Hello", paused.session_id)

    assert agent.run.await_args.args[1] == []


async def test_memory_is_limited_to_the_last_turns(agent, repository) -> None:
    service = AgentRunService(agent, repository, memory_turns=2)
    session = uuid4()
    for n in range(4):
        agent.run.return_value = done(f"answer {n}")
        await service.start(f"question {n}", session)

    remembered = agent.run.await_args.args[1]

    assert [t.question for t in remembered] == ["question 1", "question 2"]
