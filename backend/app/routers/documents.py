"""HTTP layer for documents: upload, list, delete."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status

from app.repositories.document_repository import (
    DocumentNotFoundError,
    DocumentRepository,
    get_document_repository,
)
from app.schemas.document import DocumentListResponse, DocumentSummary, DocumentUploadResponse
from app.services.extraction import FileTooLargeError
from app.services.ingestion_service import MAX_FILE_BYTES, IngestionService, get_ingestion_service

router = APIRouter(prefix="/api/documents", tags=["documents"])

Repository = Annotated[DocumentRepository, Depends(get_document_repository)]


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: Annotated[UploadFile, File(description="PDF, DOCX, TXT or MD, max 10 MB")],
    ingestion: Annotated[IngestionService, Depends(get_ingestion_service)],
    title: Annotated[str | None, Form()] = None,
) -> DocumentUploadResponse:
    # Read at most 1 byte more than allowed: enough to know it's too big,
    # without loading a huge file into memory.
    data = file.file.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise FileTooLargeError(f"The file is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB.")

    result = ingestion.ingest_file(file.filename or "upload", data, title=title)
    document = result.document
    return DocumentUploadResponse(
        id=document.id,
        title=document.title,
        source_type=document.source_type,
        file_name=document.file_name,
        created_at=document.created_at,
        chunk_count=result.chunk_count,
        page_count=result.page_count,
    )


@router.get("", response_model=DocumentListResponse)
def list_documents(repository: Repository) -> DocumentListResponse:
    return DocumentListResponse(
        documents=[DocumentSummary.from_model(d) for d in repository.list_documents()]
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: UUID, repository: Repository) -> Response:
    if repository.get_document(document_id) is None:
        raise DocumentNotFoundError(document_id)
    repository.delete_document(document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
