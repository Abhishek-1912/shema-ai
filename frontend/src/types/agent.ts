// API shapes for the tool-calling agent — must match docs/api-contract.md (version 8)
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
  run_id: string | null // always set since contract v6 (every run is saved)
  session_id: string | null // v7: send it with the next question so the agent remembers this one
  status: 'done' | 'needs_approval'
  plan: string[] // v8: steps the agent planned before acting; empty = no plan needed
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
