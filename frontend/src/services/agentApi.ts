import type { AgentRunResponse } from '../types/agent'
import { isObject, readJson, send } from './http'

// ---------------------------------------------------------------------------
// Agent endpoints (docs/api-contract.md, version 8)
// ---------------------------------------------------------------------------

// sessionId: from an earlier response → the agent remembers that conversation (v7).
export async function runAgent(question: string, sessionId?: string | null): Promise<AgentRunResponse> {
  return post('/api/agent', sessionId ? { question, session_id: sessionId } : { question })
}

// decisions: call_id → true (approve) / false (reject)
export async function sendDecisions(
  runId: string,
  decisions: Record<string, boolean>,
): Promise<AgentRunResponse> {
  return post(`/api/agent/runs/${encodeURIComponent(runId)}/decisions`, { decisions })
}

async function post(url: string, body: unknown): Promise<AgentRunResponse> {
  const response = await send(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return readJson(response, isAgentRunResponse)
}

function isAgentRunResponse(data: unknown): data is AgentRunResponse {
  return (
    isObject(data) &&
    (data.status === 'done' || data.status === 'needs_approval') &&
    typeof data.answer === 'string' &&
    Array.isArray(data.tool_calls) &&
    Array.isArray(data.pending)
  )
}
