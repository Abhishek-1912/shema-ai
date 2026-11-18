import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { askDocuments, deleteDocument, listDocuments, uploadDocument } from '../services/documentsApi'
import { ApiError } from '../services/http'
import { makeAskResponse, makeDocument, makeSource } from '../test/fixtures'
import RagPage from './RagPage'

vi.mock('../services/documentsApi', () => ({
  listDocuments: vi.fn(),
  uploadDocument: vi.fn(),
  deleteDocument: vi.fn(),
  askDocuments: vi.fn(),
}))
const listMock = vi.mocked(listDocuments)
const uploadMock = vi.mocked(uploadDocument)
const deleteMock = vi.mocked(deleteDocument)
const askMock = vi.mocked(askDocuments)

describe('RagPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    listMock.mockResolvedValue({ documents: [makeDocument('d1', 'Northwind handbook', { chunk_count: 12 })] })
  })

  it('lists the documents', async () => {
    render(<RagPage />)

    const list = await screen.findByRole('list', { name: 'Documents' })
    expect(within(list).getByText('Northwind handbook')).toBeInTheDocument()
    expect(within(list).getByText('12 chunks')).toBeInTheDocument()
  })

  it('uploads a chosen file and shows that it is ready', async () => {
    uploadMock.mockResolvedValue({ ...makeDocument('d2', 'Refund policy'), page_count: 2, chunk_count: 5 })
    const user = userEvent.setup()
    render(<RagPage />)
    await screen.findByText('Northwind handbook')

    await user.type(screen.getByLabelText('Document title'), 'Refund policy')
    await user.upload(screen.getByLabelText('Choose a document'), new File(['%PDF'], 'refund.pdf'))

    expect(await screen.findByRole('status')).toHaveTextContent('"Refund policy" is ready')
    expect(uploadMock).toHaveBeenCalledWith(expect.any(File), 'Refund policy')
  })

  it('shows why an upload failed', async () => {
    uploadMock.mockRejectedValue(new ApiError('The PDF is password-protected.', 422))
    const user = userEvent.setup()
    render(<RagPage />)
    await screen.findByText('Northwind handbook')

    await user.upload(screen.getByLabelText('Choose a document'), new File(['%PDF'], 'locked.pdf'))

    expect(await screen.findByRole('alert')).toHaveTextContent('password-protected')
  })

  it('asks a question and opens the cited source when its number is clicked', async () => {
    askMock.mockResolvedValue(
      makeAskResponse('You have 30 days [1].', [
        makeSource(1, { content: 'Customers can return any product within 30 days.', page_number: 2 }),
        makeSource(2, { cited: false, content: 'Damaged items within 7 days.', page_number: 5 }),
      ]),
    )
    const user = userEvent.setup()
    render(<RagPage />)
    await screen.findByText('Northwind handbook')

    await user.type(screen.getByRole('textbox', { name: '' }), 'How long can I return items?{Enter}')

    expect(await screen.findByText(/You have 30 days/)).toBeInTheDocument()
    expect(screen.getByText(/1 used of 2 found/)).toBeInTheDocument()
    expect(screen.queryByText('Customers can return any product within 30 days.')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Show source 1' }))

    expect(screen.getByText('Customers can return any product within 30 days.')).toBeInTheDocument()
    expect(screen.getByText('page 2')).toBeInTheDocument()
  })

  it('shows a "not found" answer without sources', async () => {
    askMock.mockResolvedValue(
      makeAskResponse("I couldn't find information about this in your documents.", [], {
        found: false,
        model: null,
        usage: null,
      }),
    )
    const user = userEvent.setup()
    render(<RagPage />)
    await screen.findByText('Northwind handbook')

    await user.type(screen.getByRole('textbox', { name: '' }), 'Who is the CEO?{Enter}')

    expect(await screen.findByText(/couldn't find information/)).toBeInTheDocument()
    expect(screen.queryByRole('list', { name: 'Sources' })).not.toBeInTheDocument()
  })

  it('deletes a document after confirmation', async () => {
    deleteMock.mockResolvedValue(undefined)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()
    render(<RagPage />)
    await screen.findByText('Northwind handbook')

    await user.click(screen.getByRole('button', { name: /delete document "Northwind handbook"/i }))

    expect(deleteMock).toHaveBeenCalledWith('d1')
    expect(await screen.findByText(/No documents yet/)).toBeInTheDocument()
  })
})
