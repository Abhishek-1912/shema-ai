import type {
  ChatRequest,
  ChatResponse,
  ConversationDetail,
  ConversationListResponse,
  Message,
} from '../types/chat'
import { isObject, readJson, send } from './http'

// The chat code calls it ChatApiError; it is the same class as the shared ApiError.
export { ApiError as ChatApiError } from './http'

// ---------------------------------------------------------------------------
// Chat + conversation endpoints (docs/api-contract.md)
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
