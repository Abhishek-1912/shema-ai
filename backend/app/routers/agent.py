"""HTTP layer for the tool-calling agent: ask, then approve/reject paused actions.

These endpoints are `async def`: the agent talks to the AI and the MCP server with
async clients, so it runs on FastAPI's event loop instead of a worker thread.
Every run is recorded in the database by AgentRunService (contract v6) and remembers earlier
questions of the same session (contract v7).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.schemas.agent import AgentRequest, AgentRunResponse, DecisionsRequest
from app.services.agent_runs import AgentRunService, get_agent_run_service

router = APIRouter(prefix="/api/agent", tags=["agent"])

Runs = Annotated[AgentRunService, Depends(get_agent_run_service)]


def _text(value: UUID | None) -> str | None:
    return str(value) if value is not None else None


@router.post("", response_model=AgentRunResponse)
async def run_agent(request: AgentRequest, runs: Runs) -> AgentRunResponse:
    recorded = await runs.start(request.question, request.session_id)
    return AgentRunResponse.from_result(recorded.result, str(recorded.run_id), _text(recorded.session_id))


@router.post("/runs/{run_id}/decisions", response_model=AgentRunResponse)
async def decide(run_id: str, request: DecisionsRequest, runs: Runs) -> AgentRunResponse:
    # Unknown, expired or already decided → RunNotFoundError → 404.
    recorded = await runs.decide(run_id, request.decisions)
    return AgentRunResponse.from_result(recorded.result, str(recorded.run_id), _text(recorded.session_id))
