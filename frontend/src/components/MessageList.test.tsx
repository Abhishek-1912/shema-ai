import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { Message } from '../types/chat'
import MessageList from './MessageList'

const messages: Message[] = [
  { id: '1', role: 'user', content: 'What is an embedding?' },
  { id: '2', role: 'assistant', content: 'A list of numbers that represents meaning.' },
]

describe('MessageList', () => {
  it('shows a hint when there are no messages', () => {
    render(<MessageList messages={[]} isLoading={false} />)

    expect(screen.getByText(/start the conversation/i)).toBeInTheDocument()
  })

  it('shows every message and hides the hint', () => {
    render(<MessageList messages={messages} isLoading={false} />)

    expect(screen.getByText('What is an embedding?')).toBeInTheDocument()
    expect(screen.getByText('A list of numbers that represents meaning.')).toBeInTheDocument()
    expect(screen.queryByText(/start the conversation/i)).not.toBeInTheDocument()
  })

  it('shows the thinking indicator only while loading', () => {
    const { rerender } = render(<MessageList messages={messages} isLoading={true} />)
    expect(screen.getByText(/thinking/i)).toBeInTheDocument()

    rerender(<MessageList messages={messages} isLoading={false} />)
    expect(screen.queryByText(/thinking/i)).not.toBeInTheDocument()
  })

  it('scrolls to the newest message', () => {
    render(<MessageList messages={messages} isLoading={false} />)

    expect(Element.prototype.scrollIntoView).toHaveBeenCalled()
  })
})
