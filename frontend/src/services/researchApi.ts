import type { ResearchResponse } from '../types/research'
import { isObject, readJson, send } from './http'

// POST /api/research (docs/api-contract.md, version 9)
export async function runResearch(question: string): Promise<ResearchResponse> {
  const response = await send('/api/research', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  return readJson(response, isResearchResponse)
}

function isResearchResponse(data: unknown): data is ResearchResponse {
  return (
    isObject(data) &&
    typeof data.run_id === 'string' &&
    typeof data.report === 'string' &&
    Array.isArray(data.sub_questions) &&
    Array.isArray(data.findings)
  )
}
