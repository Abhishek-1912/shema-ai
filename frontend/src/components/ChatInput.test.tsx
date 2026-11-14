import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import ChatInput from './ChatInput'

describe('ChatInput', () => {
  it('disables Send while the box is empty or only spaces', async () => {
    const user = userEvent.setup()
    render(<ChatInput onSend={vi.fn()} disabled={false} />)

    const sendButton = screen.getByRole('button', { name: 'Send' })
    expect(sendButton).toBeDisabled()

    await user.type(screen.getByRole('textbox'), '   ')
    expect(sendButton).toBeDisabled()
  })

  it('sends the text on Enter and clears the box', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} disabled={false} />)

    const textbox = screen.getByRole('textbox')
    await user.type(textbox, 'What is RAG?{Enter}')

    expect(onSend).toHaveBeenCalledTimes(1)
    expect(onSend).toHaveBeenCalledWith('What is RAG?')
    expect(textbox).toHaveValue('')
  })

  it('adds a new line on Shift+Enter instead of sending', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} disabled={false} />)

    const textbox = screen.getByRole('textbox')
    await user.type(textbox, 'line one{Shift>}{Enter}{/Shift}line two')

    expect(onSend).not.toHaveBeenCalled()
    expect(textbox).toHaveValue('line one\nline two')
  })

  it('sends when the Send button is clicked', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} disabled={false} />)

    await user.type(screen.getByRole('textbox'), 'Hello')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    expect(onSend).toHaveBeenCalledWith('Hello')
  })

  it('does not send while disabled (AI is still answering)', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} disabled={true} />)

    await user.type(screen.getByRole('textbox'), 'Hello{Enter}')

    expect(onSend).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
  })
})
