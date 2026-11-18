// API shapes for the research agent — must match docs/api-contract.md (version 9)
import type { TokenUsage } from './chat'
import type { ToolCall } from './agent'

export interface Finding {
  sub_question: string
  answer: string // "Not found in the documents." when the researcher found nothing
  tool_calls: ToolCall[]
  steps: number
}

export interface ResearchResponse {
  run_id: string
  question: string
  sub_questions: string[]
  findings: Finding[] // one per sub-question, same order
  report: string
  steps: number // AI calls of all agents together
  model: string | null
  usage: TokenUsage | null
}

// UI-only: one research question and its result.
export interface ResearchItem {
  id: string
  question: string
  status: 'running' | 'done' | 'error'
  response: ResearchResponse | null
  error: string | null
}
