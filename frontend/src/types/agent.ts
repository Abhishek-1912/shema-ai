// API shapes for the tool-calling agent — must match docs/api-contract.md (version 4)
import type { TokenUsage } from './chat'

export interface ToolCall {
  name: string
  arguments: Record<string, unknown>
  result: string // text, often JSON
  is_error: boolean
  duration_ms: number
  approval: 'auto' | 'approved' | 'rejected'
}

export interface PendingCall {
  call_id: string
  name: string
  arguments: Record<string, unknown>
  destructive: boolean // true = cannot be undone
}

export interface AgentRunResponse {
  run_id: string | null // set only while waiting for approval
  status: 'done' | 'needs_approval'
  answer: string
  tool_calls: ToolCall[]
  pending: PendingCall[]
  steps: number
  model: string | null
  usage: TokenUsage | null
}

// UI-only: one question to the agent and what happened.
export interface AgentItem {
  id: string
  question: string
  status: 'running' | 'needs_approval' | 'deciding' | 'done' | 'error'
  response: AgentRunResponse | null
  error: string | null
}
