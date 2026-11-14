import { afterEach, describe, expect, it, vi } from 'vitest'
import { makeChatResponse, makeMessage, makeSummary } from '../test/fixtures'
import {
  ChatApiError,
  deleteConversation,
  getConversation,
  listConversations,
  sendChat,
} from './chatApi'

// Build a fake HTTP response, like the backend would send.
function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function stubFetch(response: Response | Promise<never>) {
  const fetchMock = vi.fn().mockReturnValue(Promise.resolve(response))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

const request = { conversation_id: null, message: 'What is an LLM?' }

describe('sendChat', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('POSTs one message as JSON to /api/chat and returns the saved turn', async () => {
    const body = makeChatResponse('conv-1', 'What is an LLM?', 'An LLM is...')
    const fetchMock = stubFetch(jsonResponse(body))

    const result = await sendChat(request)

    expect(result.conversation_id).toBe('conv-1')
    expect(result.assistant_message.content).toBe('An LLM is...')
    expect(fetchMock).toHaveBeenCalledWith('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conversation_id: null, message: 'What is an LLM?' }),
    })
  })

  it('uses the backend "detail" text as the error message', async () => {
    stubFetch(jsonResponse({ detail: 'Free-tier quota used up. Try again later.' }, 429))

    const error = await sendChat(request).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ChatApiError)
    expect(error).toMatchObject({ message: 'Free-tier quota used up. Try again later.', status: 429 })
  })

  it('gives a generic message for a server error without JSON', async () => {
    stubFetch(new Response('Internal Server Error', { status: 500 }))

    await expect(sendChat(request)).rejects.toThrow(/error 500/)
  })

  it('explains when the server cannot be reached at all', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    await expect(sendChat(request)).rejects.toThrow(/cannot reach/i)
  })

  it('rejects a 200 response that does not match the contract (e.g. the old v1 shape)', async () => {
    stubFetch(jsonResponse({ reply: 'v1 shape', model: 'm', usage: null }))

    await expect(sendChat(request)).rejects.toThrow(/unexpected response/i)
  })
})

describe('conversation endpoints', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('lists conversations', async () => {
    const fetchMock = stubFetch(jsonResponse({ conversations: [makeSummary('c1', 'First chat')] }))

    const result = await listConversations()

    expect(result.conversations[0].title).toBe('First chat')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/conversations')
  })

  it('loads one conversation with its messages', async () => {
    const fetchMock = stubFetch(
      jsonResponse({
        ...makeSummary('c1', 'First chat'),
        messages: [makeMessage('user', 'Hi'), makeMessage('assistant', 'Hello')],
      }),
    )

    const result = await getConversation('c1')

    expect(result.messages.map((m) => m.content)).toEqual(['Hi', 'Hello'])
    expect(fetchMock.mock.calls[0][0]).toBe('/api/conversations/c1')
  })

  it('encodes the ID so it cannot change the URL path', async () => {
    const fetchMock = stubFetch(jsonResponse({ ...makeSummary('x', 't'), messages: [] }))

    await getConversation('../admin')

    expect(fetchMock.mock.calls[0][0]).toBe('/api/conversations/..%2Fadmin')
  })

  it('shows 404 detail when a conversation does not exist', async () => {
    stubFetch(jsonResponse({ detail: 'Conversation not found.' }, 404))

    await expect(getConversation('missing')).rejects.toMatchObject({
      message: 'Conversation not found.',
      status: 404,
    })
  })

  it('deletes with DELETE and accepts an empty 204 response', async () => {
    const fetchMock = stubFetch(new Response(null, { status: 204 }))

    await expect(deleteConversation('c1')).resolves.toBeUndefined()
    expect(fetchMock).toHaveBeenCalledWith('/api/conversations/c1', { method: 'DELETE' })
  })
})
