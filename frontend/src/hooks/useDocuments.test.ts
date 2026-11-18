import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { deleteDocument, listDocuments, uploadDocument } from '../services/documentsApi'
import { ApiError } from '../services/http'
import { makeDocument } from '../test/fixtures'
import { useDocuments, validateFile } from './useDocuments'

vi.mock('../services/documentsApi', () => ({
  listDocuments: vi.fn(),
  uploadDocument: vi.fn(),
  deleteDocument: vi.fn(),
}))
const listMock = vi.mocked(listDocuments)
const uploadMock = vi.mocked(uploadDocument)
const deleteMock = vi.mocked(deleteDocument)

function file(name: string, size = 10): File {
  return new File(['x'.repeat(size)], name)
}

async function renderDocuments() {
  const hook = renderHook(() => useDocuments())
  await waitFor(() => expect(hook.result.current.isLoading).toBe(false))
  return hook
}

describe('validateFile', () => {
  it.each(['a.pdf', 'b.DOCX', 'c.txt', 'd.md'])('accepts %s', (name) => {
    expect(validateFile(file(name))).toBeNull()
  })

  it('rejects unsupported types, empty and too large files', () => {
    expect(validateFile(file('virus.exe'))).toMatch(/not supported/)
    expect(validateFile(file('empty.pdf', 0))).toMatch(/empty/)
    const big = file('big.pdf')
    Object.defineProperty(big, 'size', { value: 11 * 1024 * 1024 })
    expect(validateFile(big)).toMatch(/larger than 10 MB/)
  })
})

describe('useDocuments', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    listMock.mockResolvedValue({ documents: [makeDocument('d1', 'Handbook')] })
  })

  it('loads the document list', async () => {
    const { result } = await renderDocuments()

    expect(result.current.documents.map((d) => d.title)).toEqual(['Handbook'])
    expect(result.current.error).toBeNull()
  })

  it('uploads, shows a success notice and refreshes the list', async () => {
    uploadMock.mockResolvedValue({ ...makeDocument('d2', 'Refund policy'), page_count: 2, chunk_count: 5 })
    const { result } = await renderDocuments()
    listMock.mockResolvedValue({
      documents: [makeDocument('d2', 'Refund policy'), makeDocument('d1', 'Handbook')],
    })

    let ok = false
    await act(async () => {
      ok = await result.current.upload(file('refund.pdf'), 'Refund policy')
    })

    expect(ok).toBe(true)
    expect(uploadMock).toHaveBeenCalledWith(expect.any(File), 'Refund policy')
    expect(result.current.notice).toMatch(/Refund policy.*2 page\(s\), 5 searchable chunks/)
    expect(result.current.documents).toHaveLength(2)
    expect(result.current.isUploading).toBe(false)
  })

  it('rejects a bad file in the browser without uploading', async () => {
    const { result } = await renderDocuments()

    await act(async () => {
      await result.current.upload(file('photo.png'))
    })

    expect(uploadMock).not.toHaveBeenCalled()
    expect(result.current.error).toMatch(/not supported/)
  })

  it('shows the backend error when the upload fails', async () => {
    uploadMock.mockRejectedValue(new ApiError('No text could be found in the file.', 422))
    const { result } = await renderDocuments()

    let ok = true
    await act(async () => {
      ok = await result.current.upload(file('scan.pdf'))
    })

    expect(ok).toBe(false)
    expect(result.current.error).toBe('No text could be found in the file.')
  })

  it('removes a deleted document from the list', async () => {
    deleteMock.mockResolvedValue(undefined)
    const { result } = await renderDocuments()

    await act(async () => {
      await result.current.remove('d1')
    })

    expect(deleteMock).toHaveBeenCalledWith('d1')
    expect(result.current.documents).toEqual([])
  })

  it('shows an error when the list cannot be loaded', async () => {
    listMock.mockRejectedValue(new ApiError('Cannot reach the Shema AI server.', null))
    const { result } = await renderDocuments()

    expect(result.current.error).toBe('Cannot reach the Shema AI server.')
  })
})
