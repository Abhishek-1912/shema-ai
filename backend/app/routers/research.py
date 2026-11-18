"""HTTP layer for the research agent (several agents on one question, read-only tools)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.schemas.research import ResearchRequest, ResearchResponse
from app.services.research import ResearchService, get_research_service

router = APIRouter(prefix="/api/research", tags=["research"])

Research = Annotated[ResearchService, Depends(get_research_service)]


@router.post("", response_model=ResearchResponse)
async def research(request: ResearchRequest, service: Research) -> ResearchResponse:
    recorded = await service.research(request.question)
    return ResearchResponse.from_result(recorded.result, str(recorded.run_id))
