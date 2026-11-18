// Small builders for fake API data, so tests stay short and match the contract.
import type { AskResponse, DocumentSummary, Source } from '../types/documents'
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

export function makeDocument(id: string, title: string, extra: Partial<DocumentSummary> = {}): DocumentSummary {
  return {
    id,
    title,
    source_type: 'pdf',
    file_name: `${id}.pdf`,
    created_at: '2026-11-18T10:00:00Z',
    chunk_count: 3,
    ...extra,
  }
}

export function makeSource(number: number, extra: Partial<Source> = {}): Source {
  return {
    number,
    cited: true,
    document_id: 'doc-1',
    document_title: 'Refund policy',
    page_number: 2,
    chunk_index: number - 1,
    content: `Source ${number} text.`,
    similarity: 0.72,
    ...extra,
  }
}

export function makeAskResponse(answer: string, sources: Source[], extra: Partial<AskResponse> = {}): AskResponse {
  return {
    answer,
    found: true,
    sources,
    model: 'gemini-test',
    usage: USAGE,
    ...extra,
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
