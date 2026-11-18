import { afterEach, describe, expect, it, vi } from 'vitest'
import { makeResearchResponse } from '../test/fixtures'
import { runResearch } from './researchApi'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

describe('researchApi', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('posts the question to /api/research', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(makeResearchResponse()))
    vi.stubGlobal('fetch', fetchMock)

    const result = await runResearch('KESTREL and the gym?')

    expect(result.findings).toHaveLength(2)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/research')
    expect(init.body).toBe(JSON.stringify({ question: 'KESTREL and the gym?' }))
  })

  it('rejects a response that does not match the contract', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ answer: 'wrong shape' })))

    await expect(runResearch('x')).rejects.toThrow(/unexpected response/i)
  })
})
