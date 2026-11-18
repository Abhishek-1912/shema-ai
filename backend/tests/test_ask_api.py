"""API tests for POST /api/ask (contract v3). RagService is a mock."""

from collections.abc import Iterator
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.document import ChunkMatch
from app.services.llm_service import LLMRateLimitError, TokenUsage
from app.services.rag_service import NOT_FOUND_ANSWER, RagAnswer, RagService, RagSource, get_rag_service

client = TestClient(app)


def make_source(number: int, cited: bool, page: int | None = 3) -> RagSource:
    chunk = ChunkMatch(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title="Refund policy",
        chunk_index=number - 1,
        page_number=page,
        content=f"Chunk {number} text.",
        similarity=0.723456,
    )
    return RagSource(number=number, chunk=chunk, cited=cited)


@pytest.fixture
def rag() -> Iterator[MagicMock]:
    fake = MagicMock(spec=RagService)
    fake.answer.return_value = RagAnswer(
        answer="You have 30 days [1].",
        sources=[make_source(1, cited=True), make_source(2, cited=False, page=None)],
        model="fake-model",
        usage=TokenUsage(input_tokens=245, output_tokens=36, thinking_tokens=0, total_tokens=281),
    )
    app.dependency_overrides[get_rag_service] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


def test_ask_returns_answer_with_sources(rag: MagicMock) -> None:
    response = client.post("/api/ask", json={"question": "How long can I return items?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "You have 30 days [1]."
    assert body["found"] is True
    assert body["model"] == "fake-model"
    assert body["usage"]["total_tokens"] == 281

    first, second = body["sources"]
    assert first["number"] == 1 and first["cited"] is True
    assert first["page_number"] == 3
    assert first["document_title"] == "Refund policy"
    assert first["similarity"] == 0.7235  # rounded for the UI
    assert second["cited"] is False and second["page_number"] is None
    rag.answer.assert_called_once_with("How long can I return items?")


def test_not_found_answer_has_found_false_and_no_sources(rag: MagicMock) -> None:
    rag.answer.return_value = RagAnswer(answer=NOT_FOUND_ANSWER, sources=[], model=None, usage=None)

    body = client.post("/api/ask", json={"question": "Who is the CEO?"}).json()

    assert body == {"answer": NOT_FOUND_ANSWER, "found": False, "sources": [], "model": None, "usage": None}


@pytest.mark.parametrize(
    "payload",
    [{}, {"question": "   "}, {"question": "x" * 2001}],
    ids=["missing", "blank", "too long"],
)
def test_invalid_question_is_422(rag: MagicMock, payload: dict) -> None:
    response = client.post("/api/ask", json=payload)

    assert response.status_code == 422
    rag.answer.assert_not_called()


def test_rate_limit_maps_to_429(rag: MagicMock) -> None:
    rag.answer.side_effect = LLMRateLimitError("quota")

    response = client.post("/api/ask", json={"question": "Anything?"})

    assert response.status_code == 429
