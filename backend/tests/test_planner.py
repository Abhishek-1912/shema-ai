"""Unit tests for the planner (plan, then act). The AI is a mock."""

from unittest.mock import AsyncMock, MagicMock

import anyio
import pytest

from app.services.planner import MAX_PLAN_STEPS, Planner, format_plan_for_agent, parse_plan
from tests.test_tool_agent import completion


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('{"steps": ["Search the documents", "Answer"]}', ["Search the documents", "Answer"]),
        ('```json\n{"steps": ["Search"]}\n```', ["Search"]),  # fenced JSON
        ('Here is the plan: {"steps": ["Search"]} Good luck', ["Search"]),
        ('{"steps": []}', []),  # simple question: no plan needed
        ('{"steps": ["  Search  ", "", 42, "List"]}', ["Search", "List"]),  # junk dropped, trimmed
    ],
)
def test_parse_plan_accepts_usable_replies(text: str, expected: list[str]) -> None:
    assert parse_plan(text) == expected


@pytest.mark.parametrize("text", [None, "", "I will search.", "{not json}", '{"plan": ["x"]}', '{"steps": "x"}', "[1]"])
def test_parse_plan_rejects_unusable_replies(text: str | None) -> None:
    assert parse_plan(text) is None


def test_parse_plan_limits_steps_and_their_length() -> None:
    steps = parse_plan('{"steps": [%s]}' % ", ".join(f'"{"x" * 500}"' for _ in range(9)))

    assert len(steps) == MAX_PLAN_STEPS
    assert all(len(s) == 200 for s in steps)


def test_format_plan_numbers_the_steps() -> None:
    text = format_plan_for_agent(["Search", "Answer"])

    assert "1. Search\n2. Answer" in text


def fake_llm(*replies: str) -> MagicMock:
    llm = MagicMock()
    llm.chat.completions.create = AsyncMock(side_effect=[completion(r) for r in replies])
    return llm


def tool(name: str, description: str) -> MagicMock:
    fake = MagicMock()
    fake.name, fake.description = name, description
    return fake


def test_plan_shows_the_tools_and_the_conversation_to_the_ai() -> None:
    llm = fake_llm('{"steps": ["Search the documents for paternity leave"]}')
    conversation = [{"role": "user", "content": "Paternity leave?"}]

    plan = anyio.run(Planner("fake-model").plan, llm, conversation, [tool("search_documents", "Search docs")])

    assert plan.steps == ["Search the documents for paternity leave"]
    assert plan.usage.total_tokens == 15
    kwargs = llm.chat.completions.create.await_args.kwargs
    assert "tools" not in kwargs  # the planner never uses tools itself
    system, *rest = kwargs["messages"]
    assert "- search_documents: Search docs" in system["content"]
    assert rest == conversation


def test_unusable_plan_becomes_an_empty_plan_not_an_error() -> None:
    llm = fake_llm("Sure! I'll search the documents.")

    plan = anyio.run(Planner("fake-model").plan, llm, [{"role": "user", "content": "Hi"}], [])

    assert plan.steps == []
