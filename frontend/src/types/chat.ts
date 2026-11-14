// Who wrote a message: the person using the app, or the AI.
export type MessageRole = 'user' | 'assistant'

// One message in a conversation (what the UI works with).
export interface Message {
  id: string
  role: MessageRole
  content: string
}

// ---------------------------------------------------------------------------
// API shapes for POST /api/chat — must match docs/api-contract.md
// ---------------------------------------------------------------------------

// A message as sent to the backend: no `id`, the backend does not need it.
export type ChatApiMessage = Pick<Message, 'role' | 'content'>

export interface ChatRequest {
  messages: ChatApiMessage[]
}

export interface TokenUsage {
  input_tokens: number
  output_tokens: number
  thinking_tokens: number
  total_tokens: number
}

export interface ChatResponse {
  reply: string
  model: string
  usage: TokenUsage | null
}
