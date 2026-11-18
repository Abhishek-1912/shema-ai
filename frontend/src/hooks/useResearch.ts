import { useState } from 'react'
import { runResearch } from '../services/researchApi'
import { ApiError } from '../services/http'
import type { ResearchItem } from '../types/research'

const GENERIC_ERROR = 'Something went wrong. Please try again.'

// Research questions on this page and their results (page state only).
export function useResearch() {
  const [items, setItems] = useState<ResearchItem[]>([])
  const isBusy = items.some((i) => i.status === 'running')

  function update(id: string, changes: Partial<ResearchItem>) {
    setItems((prev) => prev.map((item) => (item.id === id ? { ...item, ...changes } : item)))
  }

  async function ask(question: string): Promise<void> {
    const trimmed = question.trim()
    if (!trimmed || isBusy) return

    const id = crypto.randomUUID()
    setItems((prev) => [...prev, { id, question: trimmed, status: 'running', response: null, error: null }])
    try {
      update(id, { status: 'done', response: await runResearch(trimmed) })
    } catch (err) {
      update(id, { status: 'error', error: err instanceof ApiError ? err.message : GENERIC_ERROR })
    }
  }

  return { items, isBusy, ask }
}
