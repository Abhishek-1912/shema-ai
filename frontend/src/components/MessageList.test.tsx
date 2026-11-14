import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { makeMessage } from '../test/fixtures'
import type { DisplayMessage } from '../types/chat'
import MessageList from './MessageList'

const messages: DisplayMessage[] = [
  makeMessage('user', 'What is an embedding?'),
  makeMessage('assistant', 'A list of numbers that represents meaning.'),
]

describe('MessageList', () => {
  it('shows a hint when there are no messages', () => {
    render(<MessageList messages={[]} isLoading={false} error={null} />)

    expect(screen.getByText(/start the conversation/i)).toBeInTheDocument()
  })

  it('shows every message and hides the hint', () => {
    render(<MessageList messages={messages} isLoading={false} error={null} />)

    expect(screen.getByText('What is an embedding?')).toBeInTheDocument()
    expect(screen.getByText('A list of numbers that represents meaning.')).toBeInTheDocument()
    expect(screen.queryByText(/start the conversation/i)).not.toBeInTheDocument()
  })

  it('shows the thinking indicator only while loading', () => {
    const { rerender } = render(<MessageList messages={messages} isLoading={true} error={null} />)
    expect(screen.getByText(/thinking/i)).toBeInTheDocument()

    rerender(<MessageList messages={messages} isLoading={false} error={null} />)
    expect(screen.queryByText(/thinking/i)).not.toBeInTheDocument()
  })

  it('shows an error as an alert', () => {
    render(
      <MessageList messages={messages} isLoading={false} error="Cannot reach the server." />,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('Cannot reach the server.')
  })

  it('shows a loading hint instead of the empty hint while a conversation loads', () => {
    render(<MessageList messages={[]} isLoading={false} isLoadingConversation={true} error={null} />)

    expect(screen.getByText(/loading conversation/i)).toBeInTheDocument()
    expect(screen.queryByText(/start the conversation/i)).not.toBeInTheDocument()
  })

  it('marks a failed message as not sent', () => {
    const failed: DisplayMessage = { ...makeMessage('user', 'Lost question'), status: 'failed' }
    render(<MessageList messages={[failed]} isLoading={false} error={null} />)

    expect(screen.getByText(/not sent/i)).toBeInTheDocument()
  })

  it('scrolls to the newest message', () => {
    render(<MessageList messages={messages} isLoading={false} error={null} />)

    expect(Element.prototype.scrollIntoView).toHaveBeenCalled()
  })
})
