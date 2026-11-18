"""Ingestion pipeline: uploaded file → text → chunks → embeddings → database.

    file bytes ──extract──► pages of text ──chunk (per page)──► chunks + page numbers
               ──embed + store (SemanticSearchService)──► searchable document
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import PurePath

from app.core.config import get_settings
from app.models.document import Document
from app.services.chunking import chunk_text
from app.services.extraction import ExtractionError, extract_text
from app.services.search_service import SemanticSearchService, get_search_service

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB: protects memory and the free embedding quota


@dataclass(frozen=True)
class IngestedDocument:
    document: Document
    page_count: int
    chunk_count: int


def title_from_file_name(file_name: str) -> str:
    """'employee_handbook-2026.pdf' → 'Employee handbook 2026'."""
    stem = PurePath(file_name).stem
    if stem.startswith("."):  # ".txt" is a "hidden file" with no real name
        stem = ""
    stem = stem.replace("_", " ").replace("-", " ")
    stem = " ".join(stem.split())
    return stem[:1].upper() + stem[1:] if stem else "Untitled document"


class IngestionService:
    def __init__(self, search: SemanticSearchService, max_chars: int, overlap_chars: int) -> None:
        self._search = search
        self._max_chars = max_chars
        self._overlap_chars = overlap_chars

    def ingest_file(self, file_name: str, data: bytes, title: str | None = None) -> IngestedDocument:
        if len(data) > MAX_FILE_BYTES:
            raise ExtractionError(f"The file is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB.")

        # 1. Extract text (raises ExtractionError with a user-friendly message).
        extracted = extract_text(file_name, data)

        # 2. Chunk each page on its own, so every chunk knows its page number.
        chunks: list[str] = []
        page_numbers: list[int | None] = []
        for page in extracted.pages:
            for chunk in chunk_text(page.text, self._max_chars, self._overlap_chars):
                chunks.append(chunk)
                page_numbers.append(page.page_number)

        # 3 + 4. Embed and store (nothing is saved if embedding fails).
        added = self._search.add_document(
            title=(title or "").strip() or title_from_file_name(file_name),
            chunks=chunks,
            source_type=extracted.source_type,
            file_name=PurePath(file_name).name,
            page_numbers=page_numbers,
        )
        return IngestedDocument(
            document=added.document,
            page_count=extracted.page_count,
            chunk_count=added.chunk_count,
        )


@lru_cache
def get_ingestion_service() -> IngestionService:
    settings = get_settings()
    return IngestionService(get_search_service(), settings.chunk_max_chars, settings.chunk_overlap_chars)
