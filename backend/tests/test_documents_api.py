"""API tests for /api/documents (contract v3). Ingestion and repository are mocks."""

from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.document import Document, DocumentWithCount
from app.repositories.document_repository import DocumentRepository, get_document_repository
from app.routers import documents as documents_router
from app.services.extraction import ExtractionError, UnsupportedFileTypeError
from app.services.ingestion_service import IngestedDocument, IngestionService, get_ingestion_service

client = TestClient(app)
NOW = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)


def make_document(title: str = "Refund policy", **extra: object) -> Document:
    return Document(id=uuid4(), title=title, source_type="pdf", file_name="refund.pdf", created_at=NOW, **extra)


@pytest.fixture
def ingestion() -> Iterator[MagicMock]:
    fake = MagicMock(spec=IngestionService)
    fake.ingest_file.return_value = IngestedDocument(document=make_document(), page_count=3, chunk_count=7)
    app.dependency_overrides[get_ingestion_service] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


@pytest.fixture
def repo() -> Iterator[MagicMock]:
    fake = MagicMock(spec=DocumentRepository)
    app.dependency_overrides[get_document_repository] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


# --- POST /api/documents -----------------------------------------------------------

def test_upload_returns_201_with_summary(ingestion: MagicMock) -> None:
    response = client.post(
        "/api/documents",
        files={"file": ("refund.pdf", b"%PDF-fake-bytes", "application/pdf")},
        data={"title": "Refund policy"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Refund policy"
    assert body["source_type"] == "pdf"
    assert body["chunk_count"] == 7
    assert body["page_count"] == 3
    assert set(body) == {"id", "title", "source_type", "file_name", "created_at", "chunk_count", "page_count"}
    ingestion.ingest_file.assert_called_once_with("refund.pdf", b"%PDF-fake-bytes", title="Refund policy")


def test_upload_without_title_passes_none(ingestion: MagicMock) -> None:
    client.post("/api/documents", files={"file": ("notes.txt", b"hello", "text/plain")})

    assert ingestion.ingest_file.call_args.kwargs["title"] is None


def test_upload_without_file_is_422(ingestion: MagicMock) -> None:
    response = client.post("/api/documents", data={"title": "No file"})

    assert response.status_code == 422
    ingestion.ingest_file.assert_not_called()


def test_too_large_upload_is_413_and_never_ingested(
    ingestion: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(documents_router, "MAX_FILE_BYTES", 10)  # pretend the limit is 10 bytes

    response = client.post("/api/documents", files={"file": ("big.txt", b"x" * 11, "text/plain")})

    assert response.status_code == 413
    ingestion.ingest_file.assert_not_called()


def test_unsupported_type_is_415_with_the_reason(ingestion: MagicMock) -> None:
    ingestion.ingest_file.side_effect = UnsupportedFileTypeError("Unsupported file type '.exe'.")

    response = client.post("/api/documents", files={"file": ("virus.exe", b"MZ", "application/octet-stream")})

    assert response.status_code == 415
    assert response.json() == {"detail": "Unsupported file type '.exe'."}


def test_unreadable_file_is_422_with_a_user_friendly_reason(ingestion: MagicMock) -> None:
    ingestion.ingest_file.side_effect = ExtractionError("The PDF is password-protected.")

    response = client.post("/api/documents", files={"file": ("locked.pdf", b"%PDF", "application/pdf")})

    assert response.status_code == 422
    assert response.json() == {"detail": "The PDF is password-protected."}


# --- GET /api/documents ----------------------------------------------------------------

def test_list_documents_with_chunk_counts(repo: MagicMock) -> None:
    repo.list_documents.return_value = [
        DocumentWithCount(**make_document("Newest").model_dump(), chunk_count=12),
        DocumentWithCount(**make_document("Older").model_dump(), chunk_count=3),
    ]

    response = client.get("/api/documents")

    assert response.status_code == 200
    documents = response.json()["documents"]
    assert [(d["title"], d["chunk_count"]) for d in documents] == [("Newest", 12), ("Older", 3)]
    assert "user_id" not in documents[0]  # internal field is not exposed


# --- DELETE /api/documents/{id} -------------------------------------------------------------

def test_delete_document_returns_204(repo: MagicMock) -> None:
    document = make_document()
    repo.get_document.return_value = document

    response = client.delete(f"/api/documents/{document.id}")

    assert response.status_code == 204
    repo.delete_document.assert_called_once_with(document.id)


def test_delete_unknown_document_is_404(repo: MagicMock) -> None:
    repo.get_document.return_value = None

    response = client.delete(f"/api/documents/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found."}
    repo.delete_document.assert_not_called()
