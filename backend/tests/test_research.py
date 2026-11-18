"""Unit tests for the research agent: coordinator → parallel researchers → writer."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import anyio
import pytest

from app.services.llm_service import LLMRateLimitError, TokenUsage
from app.services.research import (
    ResearchService,
    format_findings,
    make_researcher,
    parse_sub_questions,
    Finding,
)
from app.services.tool_agent import AgentResult, ToolAgent, ToolCallRecord
from tests.agent_fakes import FakeRunRepository
from tests.test_tool_agent import completion, make_agent, server, search, repo, tool_call  # noqa: F401 (fixtures)

KESTREL = ToolCallRecord("search_documents", {"query": "KESTREL"}, "[...]", False, 10.0)
MONITOR = ToolCallRecord("search_documents", {"query": "monitor form"}, "[...]", False, 12.0)
USAGE = TokenUsage(input_tokens=10, output_tokens=5, thinking_tokens=0, total_tokens=15)


def fake_llm(*replies: str) -> MagicMock:
    llm = MagicMock()
    llm.chat.completions.create = AsyncMock(side_effect=[completion(r) for r in replies])
    llm.close = AsyncMock()
    return llm


def fake_researcher(answers: dict[str, AgentResult]) -> MagicMock:
    researcher = MagicMock(spec=ToolAgent)
    researcher.run = AsyncMock(side_effect=lambda question: answers[question])
    return researcher


def finding(answer: str, calls: list[ToolCallRecord]) -> AgentResult:
    return AgentResult(answer=answer, tool_calls=calls, steps=2, model="fake-model", usage=USAGE)


SUBS = '{"sub_questions": ["What is Project KESTREL?", "Which form is used to buy a monitor?"]}'
ANSWERS = {
    "What is Project KESTREL?": finding("The data warehouse migration ([demo] Forms and codes).", [KESTREL]),
    "Which form is used to buy a monitor?": finding("Form EXP-311 ([demo] Forms and codes).", [MONITOR]),
}


def make_service(llm: MagicMock, researcher: MagicMock, repository: FakeRunRepository, parallel: int = 2):
    return ResearchService(lambda: llm, "fake-model", researcher, repository, parallel=parallel)


def test_question_is_split_researched_and_written_up() -> None:
    llm = fake_llm(SUBS, "KESTREL is the data warehouse migration; use form EXP-311.")
    researcher = fake_researcher(ANSWERS)
    repository = FakeRunRepository()

    recorded = anyio.run(make_service(llm, researcher, repository).research, "  KESTREL and the monitor form?  ")

    result = recorded.result
    assert result.sub_questions == ["What is Project KESTREL?", "Which form is used to buy a monitor?"]
    assert [f.sub_question for f in result.findings] == result.sub_questions  # same order
    assert result.findings[1].answer.startswith("Form EXP-311")
    assert result.report.startswith("KESTREL is the data warehouse migration")
    # AI calls: 1 coordinator + 2 per researcher + 1 writer. Tokens: coordinator, writer and
    # each researcher's whole run (15 each in these fakes), all summed.
    assert result.steps == 6 and result.usage.total_tokens == 4 * 15
    llm.close.assert_awaited_once()


def test_writer_sees_the_question_and_every_finding_but_no_tools() -> None:
    llm = fake_llm(SUBS, "Report.")

    anyio.run(make_service(llm, fake_researcher(ANSWERS), FakeRunRepository()).research, "KESTREL and monitor?")

    writer_call = llm.chat.completions.create.call_args_list[1].kwargs
    assert "tools" not in writer_call
    content = writer_call["messages"][1]["content"]
    assert "KESTREL and monitor?" in content
    assert "Research on: What is Project KESTREL?" in content and "Form EXP-311" in content
    assert "Finding" not in content  # numbered labels got copied into reports as "sources"


def test_research_run_is_recorded_like_an_agent_run() -> None:
    llm = fake_llm(SUBS, "Report.")
    repository = FakeRunRepository()

    recorded = anyio.run(make_service(llm, fake_researcher(ANSWERS), repository).research, "KESTREL and monitor?")

    run = repository.runs[recorded.run_id]
    assert run["status"] == "done" and run["answer"] == "Report."
    assert repository.tool_calls[recorded.run_id] == [KESTREL, MONITOR]  # all researchers' calls, in order


def test_unusable_split_researches_the_whole_question() -> None:
    llm = fake_llm("I would split it like this...", "Report.")
    researcher = fake_researcher({"Paternity leave?": finding("4 weeks.", [])})

    result = anyio.run(make_service(llm, researcher, FakeRunRepository()).research, "Paternity leave?").result

    assert result.sub_questions == ["Paternity leave?"]


def test_no_more_researchers_run_at_once_than_allowed() -> None:
    running = 0
    most = 0

    async def slow(question: str) -> AgentResult:
        nonlocal running, most
        running += 1
        most = max(most, running)
        await asyncio.sleep(0.01)
        running -= 1
        return finding("ok", [])

    llm = fake_llm('{"sub_questions": ["a", "b", "c", "d"]}', "Report.")
    researcher = MagicMock(spec=ToolAgent)
    researcher.run = AsyncMock(side_effect=slow)

    anyio.run(make_service(llm, researcher, FakeRunRepository(), parallel=2).research, "Four parts?")

    assert most == 2 and researcher.run.await_count == 4


def test_a_failing_researcher_fails_the_run_and_it_is_recorded() -> None:
    llm = fake_llm(SUBS)
    researcher = MagicMock(spec=ToolAgent)
    researcher.run = AsyncMock(side_effect=LLMRateLimitError("quota"))
    repository = FakeRunRepository()

    with pytest.raises(LLMRateLimitError):
        anyio.run(make_service(llm, researcher, repository).research, "KESTREL and monitor?")

    [run] = repository.runs.values()
    assert run["status"] == "failed"
    llm.close.assert_awaited_once()  # the AI client is closed even on failure


def test_empty_question_is_refused() -> None:
    with pytest.raises(ValueError):
        anyio.run(make_service(fake_llm(), fake_researcher({}), FakeRunRepository()).research, "   ")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (SUBS, ["What is Project KESTREL?", "Which form is used to buy a monitor?"]),
        ('{"sub_questions": ["a", "b", "c", "d", "e", "f"]}', ["a", "b", "c", "d"]),  # max 4
        ('{"sub_questions": []}', []),
        ("no json", None),
    ],
)
def test_parse_sub_questions(text: str, expected: list[str] | None) -> None:
    assert parse_sub_questions(text) == expected


def test_empty_finding_is_shown_as_not_found() -> None:
    assert "Not found in the documents." in format_findings([Finding("Q?", "  ", [], 1)])


# --- The researcher only gets read-only tools ----------------------------------------

def test_researcher_is_offered_only_read_only_tools(server) -> None:  # noqa: F811
    llm = MagicMock()
    llm.chat.completions.create = AsyncMock(return_value=completion("Not found in the documents."))
    llm.close = AsyncMock()

    anyio.run(make_researcher("fake-model", server, lambda: llm).run, "Anything")

    offered = {t["function"]["name"] for t in llm.chat.completions.create.await_args.kwargs["tools"]}
    assert offered == {"search_documents", "list_documents", "list_recent_conversations"}


def test_researcher_cannot_call_a_hidden_tool(server, repo) -> None:  # noqa: F811
    llm = MagicMock()
    llm.chat.completions.create = AsyncMock(
        side_effect=[
            completion(tool_calls=[tool_call("d1", "delete_document", {"document_id": "x"})]),
            completion("Done."),
        ]
    )
    llm.close = AsyncMock()

    result = anyio.run(make_researcher("fake-model", server, lambda: llm).run, "Delete everything")

    assert result.status == "done"  # no approval pause: the tool simply doesn't exist for it
    assert result.tool_calls[0].is_error and "unknown tool" in result.tool_calls[0].result
    repo.delete_document.assert_not_called()
