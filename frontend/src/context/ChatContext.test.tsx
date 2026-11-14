import { render, renderHook, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ChatProvider } from './ChatContext'
import { useChatContext } from './useChatContext'

// A tiny component that reads the shared chat, like real pages will.
function MessageCount() {
  const { messages } = useChatContext()
  return <p>{messages.length} messages</p>
}

describe('ChatProvider', () => {
  it('gives children access to the chat', () => {
    render(
      <ChatProvider>
        <MessageCount />
      </ChatProvider>,
    )

    expect(screen.getByText('0 messages')).toBeInTheDocument()
  })

  it('throws a clear error outside the provider', () => {
    expect(() => renderHook(() => useChatContext())).toThrow(/inside <ChatProvider>/)
  })
})
