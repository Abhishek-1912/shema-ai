"""Embedding service: the ONE place that turns text into vectors.

RAG (documents), the wiki and search all call this; none of them talk to the SDK directly.
"""

import math
from functools import lru_cache

from openai import OpenAI

from app.core.ai_client import get_ai_client
from app.core.config import get_settings
from app.services.llm_service import LLMServiceError, translate_provider_errors

DEFAULT_BATCH_SIZE = 100  # max texts per API request


class EmbeddingService:
    def __init__(
        self,
        client: OpenAI,
        model: str,
        dimensions: int,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self._client = client
        self._model = model
        self._dimensions = dimensions
        self._batch_size = batch_size

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Turn many texts into vectors (same order as the input). Use this for documents."""
        if not texts:
            return []
        for position, text in enumerate(texts):
            if not text.strip():
                raise ValueError(f"Text at position {position} is empty; it cannot be embedded.")

        vectors: list[list[float]] = []
        # Send in batches: fewer requests than one-per-text, but never too many at once.
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            vectors.extend(self._embed_batch(batch))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        """Turn one search question into a vector."""
        return self.embed_texts([text])[0]

    def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        with translate_provider_errors(self._model):
            response = self._client.embeddings.create(
                model=self._model,
                input=batch,
                dimensions=self._dimensions,
            )

        # Each result carries the index of the text it belongs to; sort to be safe.
        # Gemini leaves out index 0 (Protocol Buffers skip zero values), so the SDK
        # gives us None there: fall back to the item's position in the list.
        items = [
            item for _, item in sorted(
                enumerate(response.data),
                key=lambda pair: pair[1].index if pair[1].index is not None else pair[0],
            )
        ]
        if len(items) != len(batch):
            raise LLMServiceError(
                f"Asked for {len(batch)} embeddings but received {len(items)}."
            )

        vectors = []
        for item in items:
            if len(item.embedding) != self._dimensions:
                raise LLMServiceError(
                    f"Expected {self._dimensions} numbers per embedding, "
                    f"received {len(item.embedding)}."
                )
            vectors.append(normalize(item.embedding))
        return vectors


def normalize(vector: list[float]) -> list[float]:
    """Scale a vector to length 1 (only its direction is kept).

    Shortened embeddings (e.g. 768 instead of 3072 numbers) are not length 1, and
    unit-length vectors make every similarity calculation consistent.
    """
    length = math.sqrt(sum(x * x for x in vector))
    if length == 0:
        raise LLMServiceError("The provider returned an all-zero embedding.")
    return [x / length for x in vector]


@lru_cache
def get_embedding_service() -> EmbeddingService:
    settings = get_settings()
    return EmbeddingService(
        client=get_ai_client(),
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )
