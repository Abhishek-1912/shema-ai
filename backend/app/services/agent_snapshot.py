"""Turn a paused AgentResult into plain JSON (for the database) and back.

A paused run must survive a backend restart, so everything `ToolAgent.resume()` needs
(the conversation with the AI, the pending calls, what already ran) is saved as JSON.
"""

from typing import Any

from app.services.llm_service import TokenUsage
from app.services.tool_agent import AgentResult, AgentState, PendingToolCall, ToolCallRecord, _StepItem

SNAPSHOT_VERSION = 1  # bump if the format changes; old snapshots are then refused


class SnapshotError(Exception):
    """A saved run could not be read back (unknown format)."""


def _record(record: ToolCallRecord) -> dict[str, Any]:
    return {
        "name": record.name, "arguments": record.arguments, "result": record.result,
        "is_error": record.is_error, "duration_ms": record.duration_ms, "approval": record.approval,
    }


def _pending(call: PendingToolCall) -> dict[str, Any]:
    return {"call_id": call.call_id, "name": call.name, "arguments": call.arguments, "destructive": call.destructive}


def to_snapshot(result: AgentResult) -> dict[str, Any]:
    if result.state is None:
        raise ValueError("Only a paused run (with state) can be saved for resuming.")
    state = result.state
    return {
        "version": SNAPSHOT_VERSION,
        "tool_calls": [_record(r) for r in result.tool_calls],
        "pending": [_pending(p) for p in result.pending],
        "steps": result.steps,
        "model": result.model,
        "usage": result.usage.model_dump() if result.usage else None,
        "state": {
            "messages": state.messages,
            "steps_left": state.steps_left,
            "step_items": [
                {
                    "call_id": item.call_id, "name": item.name, "arguments": item.arguments,
                    "record": _record(item.record) if item.record else None,
                }
                for item in state.step_items
            ],
            "pending": [_pending(p) for p in state.pending],
            "plan": state.plan,
        },
    }


def from_snapshot(data: dict[str, Any]) -> AgentResult:
    if data.get("version") != SNAPSHOT_VERSION:
        raise SnapshotError(f"Unknown agent run snapshot version: {data.get('version')!r}")
    raw = data["state"]
    state = AgentState(
        messages=raw["messages"],
        steps_left=raw["steps_left"],
        step_items=[
            _StepItem(
                item["call_id"], item["name"], item["arguments"],
                ToolCallRecord(**item["record"]) if item["record"] else None,
            )
            for item in raw["step_items"]
        ],
        pending=[PendingToolCall(**p) for p in raw["pending"]],
        plan=raw.get("plan"),  # missing in runs saved before planning existed
    )
    return AgentResult(
        status="needs_approval",
        tool_calls=[ToolCallRecord(**r) for r in data["tool_calls"]],
        pending=[PendingToolCall(**p) for p in data["pending"]],
        state=state,
        steps=data["steps"],
        model=data["model"],
        usage=TokenUsage(**data["usage"]) if data["usage"] else None,
        plan=list(state.plan or []),
    )
