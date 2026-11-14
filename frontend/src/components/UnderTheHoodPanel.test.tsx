import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { LastExchange } from '../types/chat'
import UnderTheHoodPanel from './UnderTheHoodPanel'

const success: LastExchange = {
  sentMessages: [
    { role: 'user', content: 'What is an LLM?' },
    { role: 'assistant', content: 'A model trained on text.' },
    { role: 'user', content: 'Give an example.' },
  ],
  durationMs: 1234,
  response: {
    reply: 'ChatGPT is one.',
    model: 'gemini-test',
    usage: { input_tokens: 5, output_tokens: 2, thinking_tokens: 0, total_tokens: 7 },
  },
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

  it('shows what was sent and what came back', () => {
    render(<UnderTheHoodPanel lastExchange={success} />)

    expect(screen.getByText('3 messages sent')).toBeInTheDocument()
    expect(screen.getByText('What is an LLM?')).toBeInTheDocument()
    expect(screen.getByText('A model trained on text.')).toBeInTheDocument()
    expect(screen.getByText('Give an example.')).toBeInTheDocument()
    expect(screen.getByText('gemini-test')).toBeInTheDocument()
    expect(valueOf('Input')).toHaveTextContent('5')
    expect(valueOf('Output')).toHaveTextContent('2')
    expect(valueOf('Thinking')).toHaveTextContent('0')
    expect(valueOf('Total')).toHaveTextContent('7')
    expect(screen.getByText('1.23 s')).toBeInTheDocument()
  })

  it('shows usage as not reported when null', () => {
    render(
      <UnderTheHoodPanel
        lastExchange={{ ...success, response: { ...success.response!, usage: null } }}
      />,
    )

    expect(screen.getByText(/not reported/i)).toBeInTheDocument()
  })

  it('shows an error with status', () => {
    render(
      <UnderTheHoodPanel
        lastExchange={{ ...success, response: null, error: { message: 'Busy', status: 503 } }}
      />,
    )

    expect(screen.getByText(/503/)).toBeInTheDocument()
    expect(screen.getByText('Busy')).toBeInTheDocument()
  })

  it('shows an error without status', () => {
    render(
      <UnderTheHoodPanel
        lastExchange={{
          ...success,
          response: null,
          error: { message: 'Cannot reach', status: null },
        }}
      />,
    )

    expect(screen.getByText('Cannot reach')).toBeInTheDocument()
    expect(screen.queryByText(/null/)).not.toBeInTheDocument()
  })
})
