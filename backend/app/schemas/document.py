"""Request/response shapes for /api/documents and /api/ask (docs/api-contract.md v3)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.document import DocumentWithCount, SourceType
from app.services.llm_service import TokenUsage
from app.services.rag_service import RagSource

MAX_QUESTION_LENGTH = 2000


class DocumentSummary(BaseModel):
    id: UUID
    title: str
    source_type: SourceType
    file_name: str | None
    created_at: datetime
    chunk_count: int

    @classmethod
    def from_model(cls, document: DocumentWithCount) -> "DocumentSummary":
        return cls(**document.model_dump(include=set(cls.model_fields)))


class DocumentUploadResponse(DocumentSummary):
    page_count: int


class DocumentListResponse(BaseModel):
    documents: list[DocumentSummary]


class AskRequest(BaseModel):
    question: str = Field(max_length=MAX_QUESTION_LENGTH)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be empty")
        return value


class SourceOut(BaseModel):
    number: int
    cited: bool
    document_id: UUID
    document_title: str
    page_number: int | None
    chunk_index: int
    content: str
    similarity: float

    @classmethod
    def from_rag(cls, source: RagSource) -> "SourceOut":
        chunk = source.chunk
        return cls(
            number=source.number,
            cited=source.cited,
            document_id=chunk.document_id,
            document_title=chunk.document_title,
            page_number=chunk.page_number,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            similarity=round(chunk.similarity, 4),
        )


class AskResponse(BaseModel):
    answer: str
    found: bool
    sources: list[SourceOut]
    model: str | None
    usage: TokenUsage | None
