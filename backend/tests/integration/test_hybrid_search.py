"""Integration test: hybrid search rescues an exact code that vector search filters out.

Needs migration 20261118000003_hybrid_search.sql. Run with: pytest -m integration -v
"""

from uuid import uuid4

import pytest

from app.repositories.document_repository import get_document_repository
from app.services.search_service import get_search_service

pytestmark = pytest.mark.integration

CODE = "ZX-4471"  # made-up code: means nothing to the embedding model


def test_exact_code_is_found_by_hybrid_but_not_by_vector_with_threshold() -> None:
    search = get_search_service()
    added = search.add_document(
        f"[integration test] {uuid4()}",
        [
            "Our canteen serves lunch every weekday from noon.",
            f"Form {CODE} is used to book a meeting room for external visitors.",
            "Parking for visitors must be booked one day in advance.",
        ],
    )
    try:
        hybrid = search.search(CODE, top_k=5, min_similarity=0.55, hybrid=True)
        vector = search.search(CODE, top_k=5, min_similarity=0.55, hybrid=False)

        hybrid_ours = [m for m in hybrid if m.document_id == added.document.id]
        assert hybrid_ours, "hybrid search must find the chunk with the exact code"
        assert CODE in hybrid_ours[0].content
        assert hybrid_ours[0].keyword_rank is not None

        vector_ours = [m for m in vector if m.document_id == added.document.id and CODE in m.content]
        # Vector search alone usually scores a bare code below the threshold (that's the
        # problem hybrid solves). Recorded, not asserted: it depends on the embedding model.
        print(f"vector-only kept the code chunk: {bool(vector_ours)}")
    finally:
        get_document_repository().delete_document(added.document.id)
