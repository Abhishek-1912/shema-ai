"""Repository for documents and their embedded chunks (pgvector)."""

from functools import lru_cache
from uuid import UUID

from postgrest.types import ReturnMethod
from supabase import Client

from app.core.supabase import get_supabase_client
from app.models.document import ChunkMatch, Document, DocumentWithCount, NewChunk, SourceType
from app.repositories.base import execute_query

DOCUMENTS = "documents"
CHUNKS = "document_chunks"
MATCH_FUNCTION = "match_document_chunks"


class DocumentNotFoundError(Exception):
    """No document exists with the given ID."""

    def __init__(self, document_id: UUID) -> None:
        super().__init__(f"Document {document_id} not found.")
        self.document_id = document_id


class DocumentRepository:
    def __init__(self, client: Client) -> None:
        self._client = client

    # Execute a query and translate library errors (shared by every repository).
    _run = staticmethod(execute_query)

    # --- Documents -----------------------------------------------------------

    def create_document(
        self,
        title: str,
        source_type: SourceType = "text",
        file_name: str | None = None,
    ) -> Document:
        rows = self._run(
            self._client.table(DOCUMENTS).insert(
                {"title": title, "source_type": source_type, "file_name": file_name}
            )
        )
        return Document.model_validate(rows[0])

    def find_document_by_title(self, title: str) -> Document | None:
        rows = self._run(self._client.table(DOCUMENTS).select("*").eq("title", title).limit(1))
        return Document.model_validate(rows[0]) if rows else None

    def get_document(self, document_id: UUID) -> Document | None:
        rows = self._run(self._client.table(DOCUMENTS).select("*").eq("id", str(document_id)))
        return Document.model_validate(rows[0]) if rows else None

    def list_documents(self) -> list[DocumentWithCount]:
        """All documents, newest first, each with its number of chunks (one query)."""
        rows = self._run(
            self._client.table(DOCUMENTS)
            # "document_chunks(count)" asks Postgres to count related chunks per document.
            .select("*, document_chunks(count)")
            .order("created_at", desc=True)
        )
        documents = []
        for row in rows:
            counts = row.pop("document_chunks", None) or [{"count": 0}]
            documents.append(DocumentWithCount(**row, chunk_count=counts[0]["count"]))
        return documents

    def delete_document(self, document_id: UUID) -> None:
        # Chunks are deleted automatically by "on delete cascade".
        self._run(self._client.table(DOCUMENTS).delete().eq("id", str(document_id)))

    # --- Chunks ----------------------------------------------------------------

    def add_chunks(self, document_id: UUID, chunks: list[NewChunk]) -> int:
        """Save many chunks in ONE insert request. Returns how many were saved."""
        if not chunks:
            return 0
        rows = [
            {
                "document_id": str(document_id),
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "page_number": chunk.page_number,
                # A Python list of floats becomes a JSON array; pgvector reads it as a vector.
                "embedding": chunk.embedding,
            }
            for chunk in chunks
        ]
        # returning="minimal": don't send 768 numbers per row back to us.
        self._run(self._client.table(CHUNKS).insert(rows, returning=ReturnMethod.minimal))
        return len(rows)

    # --- Search -------------------------------------------------------------------

    def search(
        self,
        query_embedding: list[float],
        limit: int = 5,
        min_similarity: float = 0.0,
    ) -> list[ChunkMatch]:
        """Nearest chunks by cosine similarity, best first (runs inside Postgres)."""
        rows = self._run(
            self._client.rpc(
                MATCH_FUNCTION,
                {
                    "query_embedding": query_embedding,
                    "match_count": limit,
                    "min_similarity": min_similarity,
                },
            )
        )
        return [ChunkMatch.model_validate(row) for row in rows]


@lru_cache
def get_document_repository() -> DocumentRepository:
    return DocumentRepository(get_supabase_client())
