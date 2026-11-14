import { render, renderHook, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { listConversations } from '../services/chatApi'
import { ChatProvider } from './ChatContext'
import { useChatContext } from './useChatContext'

// The provider loads the conversation list on start: fake it, never hit the network.
vi.mock('../services/chatApi', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../services/chatApi')>()),
  listConversations: vi.fn(),
}))

// A tiny component that reads the shared chat, like real pages will.
function MessageCount() {
  const { messages } = useChatContext()
  return <p>{messages.length} messages</p>
}

describe('ChatProvider', () => {
  beforeEach(() => {
    vi.mocked(listConversations).mockResolvedValue({ conversations: [] })
  })

  it('gives children access to the chat', async () => {
    render(
      <ChatProvider>
        <MessageCount />
      </ChatProvider>,
    )

    expect(await screen.findByText('0 messages')).toBeInTheDocument()
  })

  it('throws a clear error outside the provider', () => {
    expect(() => renderHook(() => useChatContext())).toThrow(/inside <ChatProvider>/)
  })
})
