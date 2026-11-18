"""Documents, chunks and search results as stored/returned by the database."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

SourceType = Literal["text", "pdf", "docx", "txt", "md"]


class Document(BaseModel):
    id: UUID
    user_id: UUID | None = None
    title: str
    source_type: SourceType
    file_name: str | None = None
    created_at: datetime


class DocumentWithCount(Document):
    """A document plus how many chunks it has (for listing)."""

    chunk_count: int


class NewChunk(BaseModel):
    """A chunk ready to be saved: its text, position and embedding."""

    chunk_index: int
    content: str
    embedding: list[float]
    page_number: int | None = None


class ChunkMatch(BaseModel):
    """One search result from match_document_chunks()."""

    chunk_id: UUID
    document_id: UUID
    document_title: str
    chunk_index: int
    page_number: int | None = None
    content: str
    similarity: float
    keyword_rank: int | None = None  # hybrid search: position in the keyword results (None = no match)
    score: float | None = None  # hybrid search: combined RRF score used for ordering
