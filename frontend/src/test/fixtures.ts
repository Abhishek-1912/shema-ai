// Small builders for fake API data, so tests stay short and match the contract.
import type { AgentRunResponse, PendingCall, ToolCall } from '../types/agent'
import type { AskResponse, DocumentSummary, Source } from '../types/documents'
import type { ArticleDetail, ArticleVersion } from '../types/wiki'
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

export function makeToolCall(name: string, extra: Partial<ToolCall> = {}): ToolCall {
  return {
    name,
    arguments: { query: 'leave' },
    result: '{"result": [{"document_title": "Handbook"}]}',
    is_error: false,
    duration_ms: 120,
    approval: 'auto',
    ...extra,
  }
}

export function makePending(callId: string, name: string, destructive = false): PendingCall {
  return { call_id: callId, name, arguments: { document_id: 'abc' }, destructive }
}

export function makeAgentResponse(extra: Partial<AgentRunResponse> = {}): AgentRunResponse {
  return {
    run_id: null,
    status: 'done',
    answer: 'Fathers get 4 weeks of paternity leave.',
    tool_calls: [makeToolCall('search_documents')],
    pending: [],
    steps: 2,
    model: 'gemini-test',
    usage: USAGE,
    ...extra,
  }
}

export function makeArticle(extra: Partial<ArticleDetail> = {}): ArticleDetail {
  return {
    slug: 'remote-work',
    title: 'Remote work',
    summary: 'Home office rules',
    status: 'draft',
    version: 2,
    created_by: 'user',
    updated_at: '2026-11-18T10:00:00Z',
    created_at: '2026-11-17T10:00:00Z',
    content: '# Rules\n\nYou may work from home **3 days** a week.',
    ...extra,
  }
}

export function makeVersion(version: number, content: string, extra: Partial<ArticleVersion> = {}): ArticleVersion {
  return {
    version,
    title: 'Remote work',
    content,
    change_note: version === 1 ? 'Created' : null,
    created_by: 'user',
    created_at: '2026-11-18T10:00:00Z',
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
