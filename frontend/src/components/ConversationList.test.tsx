import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { makeSummary } from '../test/fixtures'
import ConversationList from './ConversationList'

function renderList(onDelete = vi.fn(), path = '/chat') {
  render(
    <MemoryRouter initialEntries={[path]}>
      <ConversationList
        conversations={[makeSummary('c1', 'First chat'), makeSummary('c2', 'Second chat')]}
        onDelete={onDelete}
      />
    </MemoryRouter>,
  )
  return onDelete
}

describe('ConversationList', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('links every conversation to its URL', () => {
    renderList()

    expect(screen.getByRole('link', { name: 'First chat' })).toHaveAttribute('href', '/chat/c1')
    expect(screen.getByRole('link', { name: 'Second chat' })).toHaveAttribute('href', '/chat/c2')
    expect(screen.getByRole('link', { name: /new chat/i })).toHaveAttribute('href', '/chat')
  })

  it('highlights the open conversation', () => {
    renderList(vi.fn(), '/chat/c2')

    expect(screen.getByRole('link', { name: 'Second chat' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'First chat' })).not.toHaveAttribute('aria-current')
  })

  it('shows a hint when there are no conversations', () => {
    render(
      <MemoryRouter>
        <ConversationList conversations={[]} onDelete={vi.fn()} />
      </MemoryRouter>,
    )

    expect(screen.getByText(/no saved conversations/i)).toBeInTheDocument()
  })

  it('deletes only after the user confirms', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()
    const onDelete = renderList()

    await user.click(screen.getByRole('button', { name: /delete conversation "First chat"/i }))

    expect(confirmSpy).toHaveBeenCalled()
    expect(onDelete).toHaveBeenCalledWith('c1')
  })

  it('does nothing when the user cancels', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const user = userEvent.setup()
    const onDelete = renderList()

    await user.click(screen.getByRole('button', { name: /delete conversation "First chat"/i }))

    expect(onDelete).not.toHaveBeenCalled()
  })
})
