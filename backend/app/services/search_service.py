"""Semantic search: store text as embedded chunks, find the closest chunks for a question.

Embed ONCE when a document is added; at search time only the question is embedded.
This is the retrieval half of RAG (Module 04 adds chunking of real files and the answer step).
"""

from dataclasses import dataclass
from functools import lru_cache

from app.models.document import ChunkMatch, Document, NewChunk, SourceType
from app.repositories.base import RepositoryError
from app.repositories.document_repository import DocumentRepository, get_document_repository
from app.services.embedding_service import EmbeddingService, get_embedding_service

DEFAULT_TOP_K = 5


@dataclass(frozen=True)
class AddedDocument:
    document: Document
    chunk_count: int


class SemanticSearchService:
    def __init__(self, embedder: EmbeddingService, repository: DocumentRepository) -> None:
        self._embedder = embedder
        self._repo = repository

    def add_document(
        self,
        title: str,
        chunks: list[str],
        source_type: SourceType = "text",
        file_name: str | None = None,
        page_numbers: list[int | None] | None = None,
    ) -> AddedDocument:
        """Embed and store chunks. `page_numbers[i]` is the page of `chunks[i]` (PDFs only)."""
        if page_numbers is None:
            page_numbers = [None] * len(chunks)
        if len(page_numbers) != len(chunks):
            raise ValueError("page_numbers must have one entry per chunk.")

        pairs = [(chunk.strip(), page) for chunk, page in zip(chunks, page_numbers) if chunk.strip()]
        if not pairs:
            raise ValueError("A document needs at least one non-empty chunk.")
        texts = [text for text, _ in pairs]

        # 1. Embed first: if the AI call fails, nothing has been written to the database.
        vectors = self._embedder.embed_texts(texts)

        # 2. Save the document, then all chunks with their vectors.
        document = self._repo.create_document(title, source_type, file_name)
        new_chunks = [
            NewChunk(chunk_index=index, content=text, embedding=vector, page_number=page)
            for index, ((text, page), vector) in enumerate(zip(pairs, vectors, strict=True))
        ]
        try:
            self._repo.add_chunks(document.id, new_chunks)
        except RepositoryError:
            # Don't leave a document without chunks behind (best-effort cleanup).
            try:
                self._repo.delete_document(document.id)
            except RepositoryError:
                pass
            raise

        return AddedDocument(document=document, chunk_count=len(new_chunks))

    def search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        min_similarity: float = 0.0,
    ) -> list[ChunkMatch]:
        query = query.strip()
        if not query:
            raise ValueError("The search query must not be empty.")

        query_vector = self._embedder.embed_query(query)  # only the QUESTION is embedded now
        return self._repo.search(query_vector, limit=top_k, min_similarity=min_similarity)


@lru_cache
def get_search_service() -> SemanticSearchService:
    return SemanticSearchService(get_embedding_service(), get_document_repository())
