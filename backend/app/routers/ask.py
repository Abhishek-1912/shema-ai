"""HTTP layer for RAG questions: POST /api/ask."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.schemas.document import AskRequest, AskResponse, SourceOut
from app.services.rag_service import NOT_FOUND_ANSWER, RagService, get_rag_service

router = APIRouter(prefix="/api", tags=["ask"])


@router.post("/ask", response_model=AskResponse)
def ask(
    request: AskRequest,
    rag: Annotated[RagService, Depends(get_rag_service)],
) -> AskResponse:
    result = rag.answer(request.question)
    return AskResponse(
        answer=result.answer,
        found=result.answer.strip() != NOT_FOUND_ANSWER,
        sources=[SourceOut.from_rag(source) for source in result.sources],
        model=result.model,
        usage=result.usage,
    )
