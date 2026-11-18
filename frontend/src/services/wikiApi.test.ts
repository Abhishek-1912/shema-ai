import { afterEach, describe, expect, it, vi } from 'vitest'
import { makeArticle, makeVersion } from '../test/fixtures'
import { createArticle, listArticles, listVersions, restoreVersion, updateArticle } from './wikiApi'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

function stub(body: unknown, status = 200) {
  const fetchMock = vi.fn().mockResolvedValue(jsonResponse(body, status))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('wikiApi', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('lists articles, optionally by status', async () => {
    const fetchMock = stub({ articles: [makeArticle()] })

    const articles = await listArticles('published')

    expect(articles[0].slug).toBe('remote-work')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/wiki?status=published')
  })

  it('creates an article with POST', async () => {
    const fetchMock = stub(makeArticle({ version: 1 }), 201)

    await createArticle({ title: 'Remote work', content: 'x' })

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/wiki')
    expect(JSON.parse(init.body)).toEqual({ title: 'Remote work', content: 'x' })
  })

  it('sends the edited version as expected_version', async () => {
    const fetchMock = stub(makeArticle({ version: 3 }))

    await updateArticle('remote-work', { title: 'T', content: 'C', change_note: 'Fix' }, 2)

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/wiki/remote-work')
    expect(init.method).toBe('PUT')
    expect(JSON.parse(init.body)).toEqual({ title: 'T', content: 'C', change_note: 'Fix', expected_version: 2 })
  })

  it('turns a 409 conflict into an error with status 409', async () => {
    stub({ detail: 'Someone else changed this article after you opened it.' }, 409)

    await expect(updateArticle('remote-work', { title: 'T', content: 'C' }, 2)).rejects.toMatchObject({
      status: 409,
      message: 'Someone else changed this article after you opened it.',
    })
  })

  it('lists versions and restores one', async () => {
    const fetchMock = stub({ versions: [makeVersion(2, 'b'), makeVersion(1, 'a')] })
    expect((await listVersions('remote-work')).map((v) => v.version)).toEqual([2, 1])

    fetchMock.mockResolvedValue(jsonResponse(makeArticle({ version: 3 })))
    await restoreVersion('remote-work', 1, 2)
    const [url, init] = fetchMock.mock.calls[1]
    expect(url).toBe('/api/wiki/remote-work/restore')
    expect(JSON.parse(init.body)).toEqual({ version: 1, expected_version: 2 })
  })
})
