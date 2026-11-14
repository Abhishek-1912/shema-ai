import type { ChatApiMessage, ChatRequest, ChatResponse } from '../types/chat'

// An error with a message that is safe and useful to show to the user.
export class ChatApiError extends Error {
  readonly status: number | null

  constructor(message: string, status: number | null) {
    super(message)
    this.name = 'ChatApiError'
    this.status = status
  }
}

// The ONE place in the frontend that knows how to talk to POST /api/chat.
export async function sendChat(messages: ChatApiMessage[]): Promise<ChatResponse> {
  const body: ChatRequest = { messages }

  let response: Response
  try {
    response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  } catch {
    // fetch itself only throws when no HTTP response arrived at all (network down).
    throw new ChatApiError(
      'Cannot reach the Shema AI server. Is the backend running?',
      null,
    )
  }

  if (!response.ok) {
    throw new ChatApiError(await readErrorMessage(response), response.status)
  }

  const data: unknown = await response.json().catch(() => null)
  if (!isChatResponse(data)) {
    throw new ChatApiError('The server sent an unexpected response.', response.status)
  }
  return data
}

// FastAPI errors look like {"detail": "..."}. Use that text when it exists.
async function readErrorMessage(response: Response): Promise<string> {
  const data: unknown = await response.json().catch(() => null)
  if (
    typeof data === 'object' &&
    data !== null &&
    'detail' in data &&
    typeof data.detail === 'string'
  ) {
    return data.detail
  }
  if (response.status >= 500) {
    return `The server had a problem (error ${response.status}). Is the backend running?`
  }
  return `The request failed (error ${response.status}).`
}

// Never trust data from the network: check it really has the shape we expect.
function isChatResponse(data: unknown): data is ChatResponse {
  return (
    typeof data === 'object' &&
    data !== null &&
    'reply' in data &&
    typeof data.reply === 'string'
  )
}
