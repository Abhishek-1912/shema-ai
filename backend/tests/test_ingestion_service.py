"""Unit tests for IngestionService. The search service (embed + store) is a mock."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.models.document import Document
from app.services.extraction import ExtractionError
from app.services.ingestion_service import MAX_FILE_BYTES, IngestionService, title_from_file_name
from app.services.search_service import AddedDocument, SemanticSearchService
from scripts.simple_pdf import build_simple_pdf


@pytest.fixture
def search() -> MagicMock:
    fake = MagicMock(spec=SemanticSearchService)
    fake.add_document.side_effect = lambda title, chunks, source_type, file_name, page_numbers: AddedDocument(
        document=Document(
            id=uuid4(), title=title, source_type=source_type, file_name=file_name,
            created_at=datetime(2026, 11, 18, tzinfo=UTC),
        ),
        chunk_count=len(chunks),
    )
    return fake


def make_service(search: MagicMock) -> IngestionService:
    return IngestionService(search, max_chars=200, overlap_chars=40)


def test_pdf_chunks_keep_their_page_numbers(search: MagicMock) -> None:
    long_page = " ".join(f"Sentence {i} about refunds." for i in range(20))  # needs several chunks
    pdf = build_simple_pdf([long_page, "Leave is 15 days per year."])

    result = make_service(search).ingest_file("Refund_Policy-2026.pdf", pdf)

    kwargs = search.add_document.call_args.kwargs
    assert kwargs["title"] == "Refund Policy 2026"
    assert kwargs["source_type"] == "pdf"
    assert kwargs["file_name"] == "Refund_Policy-2026.pdf"
    pages = kwargs["page_numbers"]
    assert len(pages) == len(kwargs["chunks"])
    assert pages[0] == 1 and pages[-1] == 2
    assert pages.count(1) > 1  # page 1 was split into several chunks, all labelled page 1
    assert all(len(chunk) <= 200 for chunk in kwargs["chunks"])
    assert result.page_count == 2
    assert result.chunk_count == len(kwargs["chunks"])


def test_text_file_has_no_page_numbers(search: MagicMock) -> None:
    make_service(search).ingest_file("notes.md", b"# Notes\n\nRemote work is allowed.")

    kwargs = search.add_document.call_args.kwargs
    assert kwargs["page_numbers"] == [None]
    assert kwargs["source_type"] == "md"


def test_custom_title_wins_over_file_name(search: MagicMock) -> None:
    make_service(search).ingest_file("x.txt", b"Some text.", title="  HR Rules  ")

    assert search.add_document.call_args.kwargs["title"] == "HR Rules"


def test_too_large_file_is_rejected_before_reading(search: MagicMock) -> None:
    with pytest.raises(ExtractionError, match="larger than 10 MB"):
        make_service(search).ingest_file("big.txt", b"x" * (MAX_FILE_BYTES + 1))

    search.add_document.assert_not_called()


def test_extraction_errors_stop_the_pipeline(search: MagicMock) -> None:
    with pytest.raises(ExtractionError):
        make_service(search).ingest_file("photo.png", b"\x89PNG...")

    search.add_document.assert_not_called()


def test_only_the_file_name_is_stored_not_a_path(search: MagicMock) -> None:
    make_service(search).ingest_file("C:/Users/someone/Documents/policy.txt", b"Text.")

    assert search.add_document.call_args.kwargs["file_name"] == "policy.txt"


@pytest.mark.parametrize(
    ("file_name", "title"),
    [("employee_handbook.pdf", "Employee handbook"), ("q3-report.docx", "Q3 report"), (".txt", "Untitled document")],
)
def test_title_from_file_name(file_name: str, title: str) -> None:
    assert title_from_file_name(file_name) == title
