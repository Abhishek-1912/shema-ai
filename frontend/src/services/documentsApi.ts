import type {
  AskResponse,
  DocumentListResponse,
  DocumentUploadResponse,
} from '../types/documents'
import { isObject, readJson, send } from './http'

// ---------------------------------------------------------------------------
// Documents + RAG endpoints (docs/api-contract.md, version 3)
// ---------------------------------------------------------------------------

export async function uploadDocument(file: File, title?: string): Promise<DocumentUploadResponse> {
  // FormData = the browser's "multipart/form-data" format for file uploads.
  const form = new FormData()
  form.append('file', file)
  if (title?.trim()) form.append('title', title.trim())

  // No Content-Type header here: the browser sets it, including the "boundary"
  // string that separates the parts of the form.
  const response = await send('/api/documents', { method: 'POST', body: form })
  return readJson(response, isUploadResponse)
}

export async function listDocuments(): Promise<DocumentListResponse> {
  return readJson(await send('/api/documents'), isDocumentList)
}

export async function deleteDocument(id: string): Promise<void> {
  await send(`/api/documents/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

export async function askDocuments(question: string): Promise<AskResponse> {
  const response = await send('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  return readJson(response, isAskResponse)
}

// ---------------------------------------------------------------------------
// Shape checks
// ---------------------------------------------------------------------------

function isDocumentSummary(data: unknown): boolean {
  return (
    isObject(data) &&
    typeof data.id === 'string' &&
    typeof data.title === 'string' &&
    typeof data.chunk_count === 'number'
  )
}

function isUploadResponse(data: unknown): data is DocumentUploadResponse {
  return isDocumentSummary(data) && isObject(data) && typeof data.page_count === 'number'
}

function isDocumentList(data: unknown): data is DocumentListResponse {
  return isObject(data) && Array.isArray(data.documents) && data.documents.every(isDocumentSummary)
}

function isAskResponse(data: unknown): data is AskResponse {
  return (
    isObject(data) &&
    typeof data.answer === 'string' &&
    typeof data.found === 'boolean' &&
    Array.isArray(data.sources) &&
    data.sources.every(
      (s) => isObject(s) && typeof s.number === 'number' && typeof s.content === 'string',
    )
  )
}
