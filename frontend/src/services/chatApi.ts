import type {
  ChatRequest,
  ChatResponse,
  ConversationDetail,
  ConversationListResponse,
  Message,
} from '../types/chat'

// An error with a message that is safe and useful to show to the user.
export class ChatApiError extends Error {
  readonly status: number | null

  constructor(message: string, status: number | null) {
    super(message)
    this.name = 'ChatApiError'
    this.status = status
  }
}

// ---------------------------------------------------------------------------
// The ONLY place in the frontend that knows the backend's URLs (docs/api-contract.md)
// ---------------------------------------------------------------------------

export async function sendChat(request: ChatRequest): Promise<ChatResponse> {
  const response = await send('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  return readJson(response, isChatResponse)
}

export async function listConversations(): Promise<ConversationListResponse> {
  return readJson(await send('/api/conversations'), isConversationList)
}

export async function getConversation(id: string): Promise<ConversationDetail> {
  return readJson(await send(conversationUrl(id)), isConversationDetail)
}

export async function deleteConversation(id: string): Promise<void> {
  await send(conversationUrl(id), { method: 'DELETE' }) // 204: no body to read
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function conversationUrl(id: string): string {
  // encodeURIComponent: an ID can never break out of the URL path.
  return `/api/conversations/${encodeURIComponent(id)}`
}

// Do the request and turn every kind of failure into a ChatApiError.
async function send(url: string, init?: RequestInit): Promise<Response> {
  let response: Response
  try {
    response = await fetch(url, init)
  } catch {
    // fetch itself only throws when no HTTP response arrived at all (network down).
    throw new ChatApiError('Cannot reach the Shema AI server. Is the backend running?', null)
  }

  if (!response.ok) {
    throw new ChatApiError(await readErrorMessage(response), response.status)
  }
  return response
}

// Never trust data from the network: check it really has the shape we expect.
async function readJson<T>(response: Response, isValid: (data: unknown) => data is T): Promise<T> {
  const data: unknown = await response.json().catch(() => null)
  if (!isValid(data)) {
    throw new ChatApiError('The server sent an unexpected response.', response.status)
  }
  return data
}

// FastAPI errors look like {"detail": "..."}. Use that text when it exists.
async function readErrorMessage(response: Response): Promise<string> {
  const data: unknown = await response.json().catch(() => null)
  if (isObject(data) && typeof data.detail === 'string') {
    return data.detail
  }
  if (response.status >= 500) {
    return `The server had a problem (error ${response.status}). Is the backend running?`
  }
  return `The request failed (error ${response.status}).`
}

function isObject(data: unknown): data is Record<string, unknown> {
  return typeof data === 'object' && data !== null
}

function isMessage(data: unknown): data is Message {
  return (
    isObject(data) &&
    typeof data.id === 'string' &&
    (data.role === 'user' || data.role === 'assistant') &&
    typeof data.content === 'string'
  )
}

function isChatResponse(data: unknown): data is ChatResponse {
  return (
    isObject(data) &&
    typeof data.conversation_id === 'string' &&
    isMessage(data.user_message) &&
    isMessage(data.assistant_message)
  )
}

function isConversationList(data: unknown): data is ConversationListResponse {
  return isObject(data) && Array.isArray(data.conversations)
}

function isConversationDetail(data: unknown): data is ConversationDetail {
  return (
    isObject(data) &&
    typeof data.id === 'string' &&
    Array.isArray(data.messages) &&
    data.messages.every(isMessage)
  )
}
