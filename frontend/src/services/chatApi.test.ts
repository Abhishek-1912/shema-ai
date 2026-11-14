import { afterEach, describe, expect, it, vi } from 'vitest'
import { ChatApiError, sendChat } from './chatApi'

// Build a fake HTTP response, like the backend would send.
function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

const history = [{ role: 'user' as const, content: 'What is an LLM?' }]

describe('sendChat', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('POSTs the conversation as JSON to /api/chat and returns the reply', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ reply: 'An LLM is...', model: 'gemini-3.8-flash', usage: null }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const result = await sendChat(history)

    expect(result.reply).toBe('An LLM is...')
    expect(fetchMock).toHaveBeenCalledWith('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: history }),
    })
  })

  it('uses the backend "detail" text as the error message', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({ detail: 'Free-tier quota used up. Try again later.' }, 429),
      ),
    )

    const error = await sendChat(history).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ChatApiError)
    expect(error).toMatchObject({
      message: 'Free-tier quota used up. Try again later.',
      status: 429,
    })
  })

  it('gives a generic message for a server error without JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('Internal Server Error', { status: 500 })),
    )

    await expect(sendChat(history)).rejects.toThrow(/error 500/)
  })

  it('explains when the server cannot be reached at all', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    await expect(sendChat(history)).rejects.toThrow(/cannot reach/i)
  })

  it('rejects a 200 response that does not match the contract', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ answer: 'wrong field' })))

    await expect(sendChat(history)).rejects.toThrow(/unexpected response/i)
  })
})
