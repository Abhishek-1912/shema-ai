"""Unit tests for RagService. Search and LLM are mocks."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.models.document import ChunkMatch
from app.services.llm_service import ChatMessage, LLMResult, LLMService, LLMUnavailableError
from app.services.rag_service import (
    NOT_FOUND_ANSWER,
    RAG_SYSTEM_PROMPT,
    RagService,
    build_sources_prompt,
    find_citations,
)
from app.services.search_service import SemanticSearchService


def make_chunk(content: str, title: str = "Refund policy", index: int = 0, page: int | None = None) -> ChunkMatch:
    return ChunkMatch(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title=title,
        chunk_index=index,
        page_number=page,
        content=content,
        similarity=0.8,
    )


REFUND = make_chunk("Customers can return any product within 30 days.", index=0)
PAYBACK = make_chunk("Refunds are paid within 5 business days.", index=2)


@pytest.fixture
def search() -> MagicMock:
    fake = MagicMock(spec=SemanticSearchService)
    fake.search.return_value = [REFUND, PAYBACK]
    return fake


@pytest.fixture
def llm() -> MagicMock:
    fake = MagicMock(spec=LLMService)
    fake.chat.return_value = LLMResult(
        content="You can return products within 30 days [1].", model="fake-model"
    )
    return fake


# --- The full flow ----------------------------------------------------------------

def test_answer_retrieves_then_asks_llm_with_numbered_sources(search: MagicMock, llm: MagicMock) -> None:
    result = RagService(search, llm, top_k=4, min_similarity=0.6).answer("  Can I return things?  ")

    search.search.assert_called_once_with("Can I return things?", top_k=4, min_similarity=0.6)
    messages = llm.chat.call_args.args[0]
    assert messages == [
        ChatMessage(role="user", content=build_sources_prompt("Can I return things?", [REFUND, PAYBACK]))
    ]
    assert llm.chat.call_args.kwargs["system_prompt"] == RAG_SYSTEM_PROMPT
    assert result.answer == "You can return products within 30 days [1]."
    assert result.model == "fake-model"


def test_sources_are_numbered_and_marked_when_cited(search: MagicMock, llm: MagicMock) -> None:
    result = RagService(search, llm).answer("Can I return things?")

    assert [(s.number, s.cited) for s in result.sources] == [(1, True), (2, False)]
    assert result.sources[0].chunk == REFUND


def test_no_relevant_chunks_means_no_llm_call(search: MagicMock, llm: MagicMock) -> None:
    search.search.return_value = []

    result = RagService(search, llm).answer("Who is the CEO?")

    assert result.answer == NOT_FOUND_ANSWER
    assert result.sources == []
    llm.chat.assert_not_called()


def test_empty_question_is_rejected(search: MagicMock, llm: MagicMock) -> None:
    with pytest.raises(ValueError):
        RagService(search, llm).answer("   ")
    search.search.assert_not_called()


def test_llm_errors_are_not_hidden(search: MagicMock, llm: MagicMock) -> None:
    llm.chat.side_effect = LLMUnavailableError("overloaded")

    with pytest.raises(LLMUnavailableError):
        RagService(search, llm).answer("Can I return things?")


# --- Prompt building ----------------------------------------------------------------

def test_prompt_lists_sources_with_location_then_the_question() -> None:
    prompt = build_sources_prompt(
        "How long do refunds take?",
        [REFUND, make_chunk("Paid in 5 days.", title="Finance FAQ", index=3, page=7)],
    )

    assert prompt == (
        "Sources:\n\n"
        "[1] (Refund policy, chunk 0)\nCustomers can return any product within 30 days.\n\n"
        "[2] (Finance FAQ, chunk 3, page 7)\nPaid in 5 days.\n\n"
        "Question: How long do refunds take?"
    )


def test_system_prompt_defends_against_instructions_inside_documents() -> None:
    assert "ONLY" in RAG_SYSTEM_PROMPT
    assert "not instructions" in RAG_SYSTEM_PROMPT
    assert NOT_FOUND_ANSWER in RAG_SYSTEM_PROMPT


# --- Citation parsing -------------------------------------------------------------------

@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ("Within 30 days [1].", {1}),
        ("Yes [1][2], and also [2].", {1, 2}),
        ("See [3] and [7].", {3}),  # 7 does not exist when there are 3 sources
        ("No citations here.", set()),
        ("Weird [0] and [x].", set()),
    ],
)
def test_find_citations(answer: str, expected: set[int]) -> None:
    assert find_citations(answer, source_count=3) == expected
