"""API tests for POST /api/research (contract v9). The research service is a fake."""

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.llm_service import LLMRateLimitError, TokenUsage
from app.services.research import Finding, RecordedResearch, ResearchResult, ResearchService, get_research_service
from app.services.tool_agent import ToolCallRecord

client = TestClient(app)
RUN_ID = uuid4()
SEARCH = ToolCallRecord("search_documents", {"query": "KESTREL"}, "[...]", False, 10.04)


@pytest.fixture
def service() -> Iterator[MagicMock]:
    fake = MagicMock(spec=ResearchService)
    fake.research = AsyncMock()
    app.dependency_overrides[get_research_service] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


def test_research_returns_sub_questions_findings_and_report(service: MagicMock) -> None:
    service.research.return_value = RecordedResearch(
        RUN_ID,
        ResearchResult(
            question="KESTREL?", sub_questions=["What is Project KESTREL?"],
            findings=[Finding("What is Project KESTREL?", "Data warehouse migration.", [SEARCH], 2)],
            report="KESTREL is the data warehouse migration.", steps=4, model="fake-model",
            usage=TokenUsage(input_tokens=10, output_tokens=5, thinking_tokens=0, total_tokens=15),
        ),
    )

    response = client.post("/api/research", json={"question": "KESTREL?"})

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == str(RUN_ID)
    assert body["sub_questions"] == ["What is Project KESTREL?"]
    assert body["findings"] == [
        {
            "sub_question": "What is Project KESTREL?", "answer": "Data warehouse migration.", "steps": 2,
            "tool_calls": [{"name": "search_documents", "arguments": {"query": "KESTREL"}, "result": "[...]",
                            "is_error": False, "duration_ms": 10.0, "approval": "auto"}],
        }
    ]
    assert body["report"] == "KESTREL is the data warehouse migration."
    assert body["steps"] == 4 and body["usage"]["total_tokens"] == 15
    service.research.assert_awaited_once_with("KESTREL?")


@pytest.mark.parametrize("payload", [{}, {"question": "  "}, {"question": "x" * 2001}])
def test_invalid_question_is_422(service: MagicMock, payload: dict) -> None:
    assert client.post("/api/research", json=payload).status_code == 422
    service.research.assert_not_awaited()


def test_ai_rate_limit_is_429(service: MagicMock) -> None:
    service.research.side_effect = LLMRateLimitError("quota")

    assert client.post("/api/research", json={"question": "KESTREL?"}).status_code == 429
