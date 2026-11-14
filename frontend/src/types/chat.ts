// ---------------------------------------------------------------------------
// API shapes — must match docs/api-contract.md (version 2)
// ---------------------------------------------------------------------------

// Who wrote a message: the person using the app, or the AI.
export type MessageRole = 'user' | 'assistant'

export interface TokenUsage {
  input_tokens: number
  output_tokens: number
  thinking_tokens: number
  total_tokens: number
}

// A saved message, exactly as the backend returns it.
export interface Message {
  id: string
  role: MessageRole
  content: string
  created_at: string
  model: string | null // only for assistant messages
  usage: TokenUsage | null // only for assistant messages
}

// POST /api/chat
export interface ChatRequest {
  conversation_id: string | null // null = start a new conversation
  message: string
}

export interface ChatResponse {
  conversation_id: string
  user_message: Message
  assistant_message: Message
}

// GET /api/conversations
export interface ConversationSummary {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface ConversationListResponse {
  conversations: ConversationSummary[]
}

// GET /api/conversations/{id}
export interface ConversationDetail extends ConversationSummary {
  messages: Message[]
}

// ---------------------------------------------------------------------------
// UI-only shapes (never sent to the backend)
// ---------------------------------------------------------------------------

// A message on screen. `status` is only set while it is not saved yet:
// 'sending' = waiting for the backend, 'failed' = the backend did not save it.
export interface DisplayMessage extends Message {
  status?: 'sending' | 'failed'
}

// "Under the hood": what happened during the most recent request.
export interface LastExchange {
  request: ChatRequest // exactly what the browser sent
  historyCount: number // saved messages the backend loads from the database (max 40)
  durationMs: number
  response: ChatResponse | null // null when the request failed
  error: { message: string; status: number | null } | null
}
