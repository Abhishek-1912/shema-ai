import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AppRoutes } from './AppRoutes'
import { ChatProvider } from './context/ChatContext'
import { sendChat } from './services/chatApi'

vi.mock('./services/chatApi', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./services/chatApi')>()),
  sendChat: vi.fn(),
}))
const sendChatMock = vi.mocked(sendChat)

// MemoryRouter = a router that keeps the URL in memory, so tests can start on any page.
function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <ChatProvider>
        <AppRoutes />
      </ChatProvider>
    </MemoryRouter>,
  )
}

describe('AppRoutes', () => {
  beforeEach(() => {
    sendChatMock.mockReset()
  })

  it('redirects / to the chat', () => {
    renderAt('/')
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it('redirects unknown URLs to the chat', () => {
    renderAt('/xyz')
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it.each([
    ['/rag', 'RAG', 'Module 04'],
    ['/mcp', 'MCP', 'Module 05'],
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

  it('keeps the conversation when switching tabs', async () => {
    sendChatMock.mockResolvedValue({ reply: 'Hi there', model: 'm', usage: null })
    const user = userEvent.setup()
    renderAt('/chat')

    await user.type(screen.getByRole('textbox'), 'Hello{Enter}')
    expect(await screen.findByText('Hi there')).toBeInTheDocument()

    await user.click(screen.getByRole('link', { name: /RAG/ }))
    expect(screen.queryByText('Hi there')).not.toBeInTheDocument()

    await user.click(screen.getByRole('link', { name: /LLM Chat/ }))
    expect(screen.getAllByText('Hello').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Hi there').length).toBeGreaterThan(0)
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
