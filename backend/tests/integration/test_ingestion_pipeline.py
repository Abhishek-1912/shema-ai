"""Integration test: a real PDF goes through extract → chunk → embed → store → search.

Run with: pytest -m integration -v
"""

from uuid import uuid4

import pytest

from app.repositories.document_repository import get_document_repository
from app.services.ingestion_service import get_ingestion_service
from app.services.search_service import get_search_service
from scripts.simple_pdf import build_simple_pdf

pytestmark = pytest.mark.integration


def test_pdf_is_ingested_and_found_with_its_page_number() -> None:
    pdf = build_simple_pdf(
        [
            "Office plants are watered every Monday by the facilities team.",
            "Employees may bring their dog to the office on Thursdays if it is well behaved.",
        ]
    )
    title = f"[integration test] {uuid4()}"

    result = get_ingestion_service().ingest_file("pets.pdf", pdf, title=title)
    try:
        assert result.page_count == 2
        assert result.document.source_type == "pdf"
        assert result.document.file_name == "pets.pdf"

        matches = get_search_service().search("Can I take my puppy to work?", top_k=20)
        ours = [m for m in matches if m.document_id == result.document.id]

        assert ours, "our test document should be found"
        assert ours[0].page_number == 2  # the dog rule is on page 2
        assert "dog" in ours[0].content
    finally:
        get_document_repository().delete_document(result.document.id)
