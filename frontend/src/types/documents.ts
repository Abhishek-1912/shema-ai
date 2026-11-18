// API shapes for documents and RAG — must match docs/api-contract.md (version 3)
import type { TokenUsage } from './chat'

export type SourceType = 'pdf' | 'docx' | 'txt' | 'md' | 'text'

export interface DocumentSummary {
  id: string
  title: string
  source_type: SourceType
  file_name: string | null
  created_at: string
  chunk_count: number
}

export interface DocumentUploadResponse extends DocumentSummary {
  page_count: number
}

export interface DocumentListResponse {
  documents: DocumentSummary[]
}

// One chunk that was given to the AI as context.
export interface Source {
  number: number // the [n] used in the answer text
  cited: boolean // true if the answer contains [number]
  document_id: string
  document_title: string
  page_number: number | null
  chunk_index: number
  content: string
  similarity: number
}

export interface AskResponse {
  answer: string
  found: boolean
  sources: Source[]
  model: string | null
  usage: TokenUsage | null
}

// UI-only: one question and what happened to it (kept in memory, not saved).
export interface AskItem {
  id: string
  question: string
  status: 'loading' | 'done' | 'error'
  response: AskResponse | null
  error: string | null
}

// Same limits as the backend, checked in the browser for a faster, friendlier message.
export const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt', '.md', '.markdown'] as const
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024
