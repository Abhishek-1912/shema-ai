"""Integration test: real embeddings + real pgvector search in your Supabase project.

Needs migration 20261115000002 to be applied. Run with: pytest -m integration -v
"""

from uuid import uuid4

import pytest

from app.repositories.document_repository import get_document_repository
from app.services.search_service import get_search_service

pytestmark = pytest.mark.integration


def test_store_and_find_by_meaning() -> None:
    search = get_search_service()
    title = f"[integration test] {uuid4()}"  # unique, so it never collides with real data
    added = search.add_document(
        title,
        [
            "Customers can return products within 30 days for a full refund.",
            "Passwords must be at least 12 characters long.",
            "New employees get 15 days of paid annual leave.",
        ],
    )

    try:
        # No shared keywords with the refund chunk: must be found by meaning.
        results = search.search("How do I get my money back?", top_k=10)
        ours = [r for r in results if r.document_id == added.document.id]

        assert ours, "our test document should be among the results"
        assert ours[0].chunk_index == 0  # the refund chunk is our best match
        assert ours[0].document_title == title
        assert 0.0 < ours[0].similarity <= 1.0
        assert [r.similarity for r in results] == sorted(
            (r.similarity for r in results), reverse=True
        )
    finally:
        get_document_repository().delete_document(added.document.id)
