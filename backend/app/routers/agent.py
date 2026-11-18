"""HTTP layer for the tool-calling agent: ask, then approve/reject paused actions.

These endpoints are `async def`: the agent talks to the AI and the MCP server with
async clients, so it runs on FastAPI's event loop instead of a worker thread.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.schemas.agent import AgentRequest, AgentRunResponse, DecisionsRequest
from app.services.pending_runs import PendingRunStore, get_pending_runs
from app.services.tool_agent import AgentResult, ToolAgent, get_tool_agent

router = APIRouter(prefix="/api/agent", tags=["agent"])

Agent = Annotated[ToolAgent, Depends(get_tool_agent)]
Store = Annotated[PendingRunStore, Depends(get_pending_runs)]


def _respond(result: AgentResult, store: PendingRunStore) -> AgentRunResponse:
    # A paused run is kept on the server; the browser only gets an unguessable id.
    run_id = store.put(result) if result.status == "needs_approval" else None
    return AgentRunResponse.from_result(result, run_id)


@router.post("", response_model=AgentRunResponse)
async def run_agent(request: AgentRequest, agent: Agent, store: Store) -> AgentRunResponse:
    return _respond(await agent.run(request.question), store)


@router.post("/runs/{run_id}/decisions", response_model=AgentRunResponse)
async def decide(run_id: str, request: DecisionsRequest, agent: Agent, store: Store) -> AgentRunResponse:
    # take() removes the run: a decision is processed only ONCE (raises → 404 if unknown).
    # If resuming fails afterwards, the run is NOT put back: an approved action may
    # already have run, and retrying could do it twice. The user simply asks again.
    paused = store.take(run_id)
    return _respond(await agent.resume(paused, request.decisions), store)
