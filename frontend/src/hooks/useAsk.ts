import { useState } from 'react'
import { askDocuments } from '../services/documentsApi'
import { ApiError } from '../services/http'
import type { AskItem } from '../types/documents'

const GENERIC_ERROR = 'Something went wrong. Please try again.'

// Questions about the documents and their answers, for this browser session only.
export function useAsk() {
  const [items, setItems] = useState<AskItem[]>([])
  const isAsking = items.some((item) => item.status === 'loading')

  function update(id: string, changes: Partial<AskItem>) {
    setItems((prev) => prev.map((item) => (item.id === id ? { ...item, ...changes } : item)))
  }

  async function ask(question: string): Promise<void> {
    const trimmed = question.trim()
    if (!trimmed || isAsking) return

    const id = crypto.randomUUID()
    setItems((prev) => [
      ...prev,
      { id, question: trimmed, status: 'loading', response: null, error: null },
    ])

    try {
      const response = await askDocuments(trimmed)
      update(id, { status: 'done', response })
    } catch (err) {
      update(id, { status: 'error', error: err instanceof ApiError ? err.message : GENERIC_ERROR })
    }
  }

  return { items, isAsking, ask, clear: () => setItems([]) }
}
