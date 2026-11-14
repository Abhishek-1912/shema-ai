import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { makeChatResponse } from '../test/fixtures'
import type { LastExchange } from '../types/chat'
import UnderTheHoodPanel from './UnderTheHoodPanel'

const success: LastExchange = {
  request: { conversation_id: 'conv-123', message: 'Give an example.' },
  historyCount: 2,
  durationMs: 1234,
  response: makeChatResponse('conv-123', 'Give an example.', 'ChatGPT is one.'),
  error: null,
}

// The value shown right after a label, e.g. "Input" → "5".
function valueOf(label: string) {
  return screen.getByText(label).nextElementSibling
}

describe('UnderTheHoodPanel', () => {
  it('explains itself before the first message', () => {
    render(<UnderTheHoodPanel lastExchange={null} />)

    expect(screen.getByRole('complementary', { name: 'Under the hood' })).toBeInTheDocument()
    expect(screen.getByText(/send a message/i)).toBeInTheDocument()
  })

  it('shows that only one message was sent and what the backend added', () => {
    render(<UnderTheHoodPanel lastExchange={success} />)

    expect(screen.getByText('1 new message sent')).toBeInTheDocument()
    expect(screen.getByText('Give an example.')).toBeInTheDocument()
    expect(screen.getByText('conv-123')).toBeInTheDocument()
    expect(screen.getByText(/system prompt/i)).toBeInTheDocument()
    expect(screen.getByText('2 earlier messages from the database')).toBeInTheDocument()
  })

  it('says when a new conversation is being created', () => {
    render(
      <UnderTheHoodPanel
        lastExchange={{
          ...success,
          request: { conversation_id: null, message: 'Hi' },
          historyCount: 0,
        }}
      />,
    )

    expect(screen.getByText(/new \(the backend creates it\)/i)).toBeInTheDocument()
    expect(screen.getByText('0 earlier messages from the database')).toBeInTheDocument()
  })

  it('shows model, tokens, time and that it was saved', () => {
    render(<UnderTheHoodPanel lastExchange={success} />)

    expect(screen.getByText('gemini-test')).toBeInTheDocument()
    expect(valueOf('Input')).toHaveTextContent('5')
    expect(valueOf('Output')).toHaveTextContent('2')
    expect(valueOf('Thinking')).toHaveTextContent('0')
    expect(valueOf('Total')).toHaveTextContent('7')
    expect(screen.getByText('1.23 s')).toBeInTheDocument()
    expect(screen.getByText(/saved to the database/i)).toBeInTheDocument()
  })

  it('shows usage as not reported when null', () => {
    const response = makeChatResponse('conv-123', 'q', 'a')
    response.assistant_message.usage = null
    render(<UnderTheHoodPanel lastExchange={{ ...success, response }} />)

    expect(screen.getByText(/not reported/i)).toBeInTheDocument()
  })

  it('shows an error with status and that nothing was saved', () => {
    render(
      <UnderTheHoodPanel
        lastExchange={{ ...success, response: null, error: { message: 'Busy', status: 503 } }}
      />,
    )

    expect(screen.getByText(/503/)).toBeInTheDocument()
    expect(screen.getByText('Busy')).toBeInTheDocument()
    expect(screen.getByText(/nothing was saved/i)).toBeInTheDocument()
    expect(screen.queryByText(/saved to the database/i)).not.toBeInTheDocument()
  })

  it('shows an error without status', () => {
    render(
      <UnderTheHoodPanel
        lastExchange={{ ...success, response: null, error: { message: 'Cannot reach', status: null } }}
      />,
    )

    expect(screen.getByText('Cannot reach')).toBeInTheDocument()
    expect(screen.queryByText(/null/)).not.toBeInTheDocument()
  })
})
