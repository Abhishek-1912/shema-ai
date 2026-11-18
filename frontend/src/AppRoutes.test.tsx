import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, useLocation } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AppRoutes } from './AppRoutes'
import { ChatProvider } from './context/ChatContext'
import {
  deleteConversation,
  getConversation,
  listConversations,
  sendChat,
} from './services/chatApi'
import { listDocuments } from './services/documentsApi'
import { makeChatResponse, makeMessage, makeSummary } from './test/fixtures'

vi.mock('./services/chatApi', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./services/chatApi')>()),
  sendChat: vi.fn(),
  listConversations: vi.fn(),
  getConversation: vi.fn(),
  deleteConversation: vi.fn(),
}))
const sendChatMock = vi.mocked(sendChat)

// The RAG page loads its document list on start: fake it too.
vi.mock('./services/documentsApi', () => ({
  listDocuments: vi.fn(),
  uploadDocument: vi.fn(),
  deleteDocument: vi.fn(),
  askDocuments: vi.fn(),
}))
const listDocumentsMock = vi.mocked(listDocuments)
const listMock = vi.mocked(listConversations)
const getMock = vi.mocked(getConversation)
const deleteMock = vi.mocked(deleteConversation)

// Shows the current URL so tests can check navigation.
function CurrentPath() {
  return <p data-testid="path">{useLocation().pathname}</p>
}

// MemoryRouter = a router that keeps the URL in memory, so tests can start on any page.
function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <ChatProvider>
        <AppRoutes />
        <CurrentPath />
      </ChatProvider>
    </MemoryRouter>,
  )
}

describe('AppRoutes', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    listMock.mockResolvedValue({ conversations: [] })
    listDocumentsMock.mockResolvedValue({ documents: [] }) // reset above wipes it, so set it again
  })

  it('redirects / to the chat', () => {
    renderAt('/')
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it('redirects unknown URLs to the chat', () => {
    renderAt('/xyz')
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it('shows the real RAG page at /rag', async () => {
    renderAt('/rag')
    expect(screen.getByRole('heading', { level: 1, name: 'Ask your documents' })).toBeInTheDocument()
    expect(await screen.findByText(/No documents yet/)).toBeInTheDocument()
  })

  it('shows the real agent page at /mcp', () => {
    renderAt('/mcp')
    expect(screen.getByRole('heading', { level: 1, name: 'Agent with tools (MCP)' })).toBeInTheDocument()
  })

  it.each([
    ['/wiki', 'LLM Wiki', 'Module 06'],
  ])('shows the concept page at %s', (path, title, module) => {
    renderAt(path)
    expect(screen.getByRole('heading', { level: 1, name: title })).toBeInTheDocument()
    expect(screen.getByText(new RegExp(`Coming in ${module}`))).toBeInTheDocument()
  })

  it('highlights the active tab', () => {
    renderAt('/rag')
    expect(screen.getByRole('link', { name: /RAG/ })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: /LLM Chat/ })).not.toHaveAttribute('aria-current')
  })

  it('puts a new conversation into the URL after the first reply', async () => {
    sendChatMock.mockResolvedValue(makeChatResponse('conv-1', 'Hello', 'Hi there'))
    const user = userEvent.setup()
    renderAt('/chat')

    await user.type(screen.getByRole('textbox'), 'Hello{Enter}')

    expect(await screen.findByText('Hi there')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('path')).toHaveTextContent('/chat/conv-1'))
    expect(getMock).not.toHaveBeenCalled() // the new chat is already on screen: no reload
  })

  it('opens a saved conversation from the URL (what a page refresh does)', async () => {
    getMock.mockResolvedValue({
      ...makeSummary('conv-9', 'Saved chat'),
      messages: [makeMessage('user', 'Saved question'), makeMessage('assistant', 'Saved answer')],
    })
    renderAt('/chat/conv-9')

    expect(await screen.findByText('Saved answer')).toBeInTheDocument()
    expect(getMock).toHaveBeenCalledWith('conv-9')
  })

  it('opens a conversation from the sidebar and starts a new chat', async () => {
    listMock.mockResolvedValue({ conversations: [makeSummary('conv-9', 'Saved chat')] })
    getMock.mockResolvedValue({
      ...makeSummary('conv-9', 'Saved chat'),
      messages: [makeMessage('user', 'Saved question')],
    })
    const user = userEvent.setup()
    renderAt('/chat')

    await user.click(await screen.findByRole('link', { name: 'Saved chat' }))
    expect(await screen.findByText('Saved question')).toBeInTheDocument()
    expect(screen.getByTestId('path')).toHaveTextContent('/chat/conv-9')

    await user.click(screen.getByRole('link', { name: /new chat/i }))
    expect(screen.queryByText('Saved question')).not.toBeInTheDocument()
    expect(screen.getByTestId('path')).toHaveTextContent(/^\/chat$/)
  })

  it('deletes the open conversation and goes back to a new chat', async () => {
    listMock.mockResolvedValue({ conversations: [makeSummary('conv-9', 'Saved chat')] })
    getMock.mockResolvedValue({
      ...makeSummary('conv-9', 'Saved chat'),
      messages: [makeMessage('user', 'Saved question')],
    })
    deleteMock.mockResolvedValue(undefined)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()
    renderAt('/chat/conv-9')
    await screen.findByText('Saved question')

    await user.click(screen.getByRole('button', { name: /delete conversation "Saved chat"/i }))

    await waitFor(() => expect(screen.getByTestId('path')).toHaveTextContent(/^\/chat$/))
    expect(deleteMock).toHaveBeenCalledWith('conv-9')
    expect(screen.queryByRole('link', { name: 'Saved chat' })).not.toBeInTheDocument()
  })

  it('keeps the conversation when switching tabs', async () => {
    sendChatMock.mockResolvedValue(makeChatResponse('conv-1', 'Hello', 'Hi there'))
    const user = userEvent.setup()
    renderAt('/chat')

    await user.type(screen.getByRole('textbox'), 'Hello{Enter}')
    expect(await screen.findByText('Hi there')).toBeInTheDocument()

    await user.click(screen.getByRole('link', { name: /RAG/ }))
    expect(screen.queryByText('Hi there')).not.toBeInTheDocument()

    await user.click(screen.getByRole('link', { name: /LLM Chat/ }))
    expect(screen.getAllByText('Hello').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Hi there').length).toBeGreaterThan(0)
    expect(screen.getByTestId('path')).toHaveTextContent('/chat/conv-1')
    expect(getMock).not.toHaveBeenCalled()
  })

  it('hides and shows the panel', async () => {
    const user = userEvent.setup()
    renderAt('/chat')

    expect(screen.getByRole('complementary', { name: 'Under the hood' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /hide under the hood/i }))
    expect(screen.queryByRole('complementary', { name: 'Under the hood' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /show under the hood/i }))
    expect(screen.getByRole('complementary', { name: 'Under the hood' })).toBeInTheDocument()
  })
})
