import { afterEach, describe, expect, it, vi } from 'vitest'
import { makeAskResponse, makeDocument, makeSource } from '../test/fixtures'
import { askDocuments, deleteDocument, listDocuments, uploadDocument } from './documentsApi'
import { ApiError } from './http'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

function stubFetch(response: Response) {
  const fetchMock = vi.fn().mockResolvedValue(response)
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

const pdf = new File(['%PDF-fake'], 'refund.pdf', { type: 'application/pdf' })

describe('documentsApi', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('uploads the file and title as multipart form data', async () => {
    const fetchMock = stubFetch(jsonResponse({ ...makeDocument('d1', 'Refund'), page_count: 2 }, 201))

    const result = await uploadDocument(pdf, '  Refund policy  ')

    expect(result.page_count).toBe(2)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/documents')
    expect(init.method).toBe('POST')
    expect(init.headers).toBeUndefined() // the browser must set the multipart boundary itself
    const form = init.body as FormData
    expect((form.get('file') as File).name).toBe('refund.pdf')
    expect(form.get('title')).toBe('Refund policy')
  })

  it('leaves out an empty title', async () => {
    const fetchMock = stubFetch(jsonResponse({ ...makeDocument('d1', 'Refund'), page_count: 1 }, 201))

    await uploadDocument(pdf, '   ')

    expect((fetchMock.mock.calls[0][1].body as FormData).has('title')).toBe(false)
  })

  it('shows the backend reason when a file is rejected', async () => {
    stubFetch(jsonResponse({ detail: 'The PDF is password-protected.' }, 422))

    const error = await uploadDocument(pdf).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ message: 'The PDF is password-protected.', status: 422 })
  })

  it('lists documents', async () => {
    stubFetch(jsonResponse({ documents: [makeDocument('d1', 'Handbook')] }))

    const result = await listDocuments()

    expect(result.documents[0].title).toBe('Handbook')
  })

  it('deletes with DELETE and an encoded id', async () => {
    const fetchMock = stubFetch(new Response(null, { status: 204 }))

    await deleteDocument('a/b')

    expect(fetchMock).toHaveBeenCalledWith('/api/documents/a%2Fb', { method: 'DELETE' })
  })

  it('asks a question as JSON and returns the answer with sources', async () => {
    const fetchMock = stubFetch(jsonResponse(makeAskResponse('30 days [1].', [makeSource(1)])))

    const result = await askDocuments('How long?')

    expect(result.sources[0].number).toBe(1)
    expect(fetchMock.mock.calls[0][1].body).toBe(JSON.stringify({ question: 'How long?' }))
  })

  it('rejects an ask response that does not match the contract', async () => {
    stubFetch(jsonResponse({ reply: 'wrong shape' }))

    await expect(askDocuments('x')).rejects.toThrow(/unexpected response/i)
  })
})
