import { useState } from 'react'
import { runAgent, sendDecisions } from '../services/agentApi'
import { ApiError } from '../services/http'
import type { AgentItem, AgentRunResponse } from '../types/agent'

const GENERIC_ERROR = 'Something went wrong. Please try again.'

function messageOf(err: unknown): string {
  return err instanceof ApiError ? err.message : GENERIC_ERROR
}

function statusOf(response: AgentRunResponse): AgentItem['status'] {
  return response.status === 'needs_approval' ? 'needs_approval' : 'done'
}

// Questions to the tool-using agent, their tool calls, and pending approvals (session only).
export function useAgent() {
  const [items, setItems] = useState<AgentItem[]>([])
  const isBusy = items.some((i) => i.status === 'running' || i.status === 'deciding')

  function update(id: string, changes: Partial<AgentItem>) {
    setItems((prev) => prev.map((item) => (item.id === id ? { ...item, ...changes } : item)))
  }

  async function ask(question: string): Promise<void> {
    const trimmed = question.trim()
    if (!trimmed || isBusy) return

    const id = crypto.randomUUID()
    setItems((prev) => [...prev, { id, question: trimmed, status: 'running', response: null, error: null }])
    try {
      const response = await runAgent(trimmed)
      update(id, { status: statusOf(response), response })
    } catch (err) {
      update(id, { status: 'error', error: messageOf(err) })
    }
  }

  // Send the human's approve/reject decisions for a paused run.
  async function decide(id: string, decisions: Record<string, boolean>): Promise<void> {
    const item = items.find((i) => i.id === id)
    const runId = item?.response?.run_id
    if (!item || item.status !== 'needs_approval' || !runId) return

    update(id, { status: 'deciding' })
    try {
      const response = await sendDecisions(runId, decisions)
      update(id, { status: statusOf(response), response })
    } catch (err) {
      update(id, { status: 'error', error: messageOf(err) })
    }
  }

  return { items, isBusy, ask, decide }
}
