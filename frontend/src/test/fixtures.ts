// Small builders for fake API data, so tests stay short and match the contract.
import type {
  ChatResponse,
  ConversationSummary,
  Message,
  MessageRole,
  TokenUsage,
} from '../types/chat'

let counter = 0
function nextId(prefix: string): string {
  counter += 1
  return `${prefix}-${counter}`
}

export const USAGE: TokenUsage = {
  input_tokens: 5,
  output_tokens: 2,
  thinking_tokens: 0,
  total_tokens: 7,
}

export function makeMessage(role: MessageRole, content: string, extra: Partial<Message> = {}): Message {
  return {
    id: nextId('msg'),
    role,
    content,
    created_at: '2026-11-15T10:00:00Z',
    model: role === 'assistant' ? 'gemini-test' : null,
    usage: role === 'assistant' ? USAGE : null,
    ...extra,
  }
}

export function makeChatResponse(
  conversationId: string,
  question: string,
  reply: string,
): ChatResponse {
  return {
    conversation_id: conversationId,
    user_message: makeMessage('user', question),
    assistant_message: makeMessage('assistant', reply),
  }
}

export function makeSummary(id: string, title: string): ConversationSummary {
  return {
    id,
    title,
    created_at: '2026-11-15T10:00:00Z',
    updated_at: '2026-11-15T10:00:00Z',
  }
}
