"""Unit tests for SemanticSearchService. Embedder and repository are mocks."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.models.document import ChunkMatch, Document, NewChunk
from app.repositories.base import RepositoryError
from app.repositories.document_repository import DocumentRepository
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMUnavailableError
from app.services.search_service import SemanticSearchService

DOCUMENT = Document(
    id=uuid4(), title="Refund policy", source_type="text", created_at=datetime(2026, 11, 18, tzinfo=UTC)
)


@pytest.fixture
def embedder() -> MagicMock:
    fake = MagicMock(spec=EmbeddingService)
    fake.embed_texts.side_effect = lambda texts: [[float(i), 0.0] for i in range(len(texts))]
    fake.embed_query.return_value = [0.5, 0.5]
    return fake


@pytest.fixture
def repo() -> MagicMock:
    fake = MagicMock(spec=DocumentRepository)
    fake.create_document.return_value = DOCUMENT
    return fake


# --- Adding documents -------------------------------------------------------------

def test_add_document_embeds_chunks_and_saves_them_in_order(embedder: MagicMock, repo: MagicMock) -> None:
    added = SemanticSearchService(embedder, repo).add_document(
        "Refund policy", ["  First part.  ", "", "Second part."]
    )

    embedder.embed_texts.assert_called_once_with(["First part.", "Second part."])  # blank skipped
    repo.create_document.assert_called_once_with("Refund policy", "text", None)
    repo.add_chunks.assert_called_once_with(
        DOCUMENT.id,
        [
            NewChunk(chunk_index=0, content="First part.", embedding=[0.0, 0.0]),
            NewChunk(chunk_index=1, content="Second part.", embedding=[1.0, 0.0]),
        ],
    )
    assert added.chunk_count == 2
    assert added.document == DOCUMENT


def test_page_numbers_are_saved_with_each_chunk(embedder: MagicMock, repo: MagicMock) -> None:
    SemanticSearchService(embedder, repo).add_document(
        "Policy", ["Page one.", "  ", "Page three."], page_numbers=[1, 2, 3]
    )

    saved = repo.add_chunks.call_args.args[1]
    assert [(c.content, c.page_number) for c in saved] == [("Page one.", 1), ("Page three.", 3)]


def test_page_numbers_must_match_chunks(embedder: MagicMock, repo: MagicMock) -> None:
    with pytest.raises(ValueError, match="one entry per chunk"):
        SemanticSearchService(embedder, repo).add_document("Policy", ["a", "b"], page_numbers=[1])


def test_document_without_text_is_rejected(embedder: MagicMock, repo: MagicMock) -> None:
    with pytest.raises(ValueError):
        SemanticSearchService(embedder, repo).add_document("Empty", ["   ", ""])

    embedder.embed_texts.assert_not_called()
    repo.create_document.assert_not_called()


def test_embedding_failure_saves_nothing(embedder: MagicMock, repo: MagicMock) -> None:
    embedder.embed_texts.side_effect = LLMUnavailableError("overloaded")

    with pytest.raises(LLMUnavailableError):
        SemanticSearchService(embedder, repo).add_document("Doc", ["text"])

    repo.create_document.assert_not_called()


def test_chunk_save_failure_removes_the_half_saved_document(embedder: MagicMock, repo: MagicMock) -> None:
    repo.add_chunks.side_effect = RepositoryError("insert failed")

    with pytest.raises(RepositoryError):
        SemanticSearchService(embedder, repo).add_document("Doc", ["text"])

    repo.delete_document.assert_called_once_with(DOCUMENT.id)


# --- Searching --------------------------------------------------------------------------

def test_search_embeds_only_the_query_and_asks_the_database(embedder: MagicMock, repo: MagicMock) -> None:
    match = ChunkMatch(
        chunk_id=uuid4(),
        document_id=DOCUMENT.id,
        document_title="Refund policy",
        chunk_index=0,
        content="Refunds within 30 days.",
        similarity=0.82,
    )
    repo.search.return_value = [match]

    results = SemanticSearchService(embedder, repo).search("  money back?  ", top_k=3)

    embedder.embed_query.assert_called_once_with("money back?")
    embedder.embed_texts.assert_not_called()  # documents are NOT re-embedded
    repo.search.assert_called_once_with([0.5, 0.5], limit=3, min_similarity=0.0)
    assert results == [match]


def test_empty_query_is_rejected(embedder: MagicMock, repo: MagicMock) -> None:
    with pytest.raises(ValueError):
        SemanticSearchService(embedder, repo).search("   ")

    embedder.embed_query.assert_not_called()
