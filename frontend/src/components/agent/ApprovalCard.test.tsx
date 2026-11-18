import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { makePending } from '../../test/fixtures'
import ApprovalCard from './ApprovalCard'

describe('ApprovalCard', () => {
  it('shows a strong warning for destructive actions and the arguments', () => {
    render(<ApprovalCard pending={[makePending('d1', 'delete_document', true)]} disabled={false} onDecide={vi.fn()} />)

    expect(screen.getByText(/destructive: cannot be undone/i)).toBeInTheDocument()
    expect(screen.getByText(/"document_id": "abc"/)).toBeInTheDocument()
    expect(screen.getByText(/Nothing has happened yet/)).toBeInTheDocument()
  })

  it('sends the decision when the only action is approved', async () => {
    const onDecide = vi.fn()
    const user = userEvent.setup()
    render(<ApprovalCard pending={[makePending('d1', 'delete_document', true)]} disabled={false} onDecide={onDecide} />)

    await user.click(screen.getByRole('button', { name: 'Approve delete_document' }))

    expect(onDecide).toHaveBeenCalledWith({ d1: true })
  })

  it('waits until every pending action has a decision', async () => {
    const onDecide = vi.fn()
    const user = userEvent.setup()
    render(
      <ApprovalCard
        pending={[makePending('s1', 'save_note'), makePending('d1', 'delete_document', true)]}
        disabled={false}
        onDecide={onDecide}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Approve save_note' }))
    expect(onDecide).not.toHaveBeenCalled()
    expect(screen.getByText('You approved this.')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Reject delete_document' }))
    expect(onDecide).toHaveBeenCalledWith({ s1: true, d1: false })
  })

  it('disables the buttons while a decision is being sent', () => {
    render(<ApprovalCard pending={[makePending('s1', 'save_note')]} disabled={true} onDecide={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Approve save_note' })).toBeDisabled()
    expect(screen.getByText('changes data')).toBeInTheDocument()
  })
})
