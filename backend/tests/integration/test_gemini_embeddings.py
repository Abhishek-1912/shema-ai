"""Integration test: calls the REAL embedding model. Run with: pytest -m integration -v"""

import math

import pytest

from app.services.embedding_service import get_embedding_service

pytestmark = pytest.mark.integration


def dot(a: list[float], b: list[float]) -> float:
    # Vectors are normalized, so the dot product IS the cosine similarity.
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_real_embeddings_capture_meaning() -> None:
    service = get_embedding_service()

    cat, kitten, stocks = service.embed_texts(
        [
            "The cat sat on the mat.",
            "A kitten was resting on the rug.",
            "The stock market fell sharply today.",
        ]
    )

    assert len(cat) == service.dimensions
    assert math.sqrt(dot(cat, cat)) == pytest.approx(1.0)
    # Same meaning (no shared words) must beat different meaning.
    assert dot(cat, kitten) > dot(cat, stocks)
