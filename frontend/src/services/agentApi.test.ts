import { afterEach, describe, expect, it, vi } from 'vitest'
import { makeAgentResponse } from '../test/fixtures'
import { runAgent, sendDecisions } from './agentApi'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

describe('agentApi', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('posts the question to /api/agent', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(makeAgentResponse()))
    vi.stubGlobal('fetch', fetchMock)

    const result = await runAgent('Paternity leave?')

    expect(result.status).toBe('done')
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/agent')
    expect(init.body).toBe(JSON.stringify({ question: 'Paternity leave?' }))
  })

  it('sends the session id with a follow-up question', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(makeAgentResponse()))
    vi.stubGlobal('fetch', fetchMock)

    await runAgent('And for mothers?', 'session-1')

    expect(fetchMock.mock.calls[0][1].body).toBe(
      JSON.stringify({ question: 'And for mothers?', session_id: 'session-1' }),
    )
  })

  it('sends decisions to the run with an encoded id', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(makeAgentResponse()))
    vi.stubGlobal('fetch', fetchMock)

    await sendDecisions('a/b', { d1: true, d2: false })

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/agent/runs/a%2Fb/decisions')
    expect(init.body).toBe(JSON.stringify({ decisions: { d1: true, d2: false } }))
  })

  it('shows the 404 reason for an expired run', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'This approval request has expired.' }, 404)),
    )

    await expect(sendDecisions('old', {})).rejects.toMatchObject({ status: 404, message: 'This approval request has expired.' })
  })

  it('rejects a response that does not match the contract', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ reply: 'wrong' })))

    await expect(runAgent('x')).rejects.toThrow(/unexpected response/i)
  })
})
