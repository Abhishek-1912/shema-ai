import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { runAgent, sendDecisions } from '../services/agentApi'
import { makeAgentResponse, makePending, makeToolCall } from '../test/fixtures'
import AgentPage from './AgentPage'

vi.mock('../services/agentApi', () => ({ runAgent: vi.fn(), sendDecisions: vi.fn() }))
const runMock = vi.mocked(runAgent)
const decideMock = vi.mocked(sendDecisions)

describe('AgentPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('offers example questions and runs one when clicked', async () => {
    runMock.mockResolvedValue(makeAgentResponse())
    const user = userEvent.setup()
    render(<AgentPage />)

    await user.click(screen.getByRole('button', { name: /Which documents do we have/ }))

    expect(runMock).toHaveBeenCalledWith('Which documents do we have, and how long is paternity leave?')
    expect(await screen.findByText('Fathers get 4 weeks of paternity leave.')).toBeInTheDocument()
  })

  it('shows every tool call and its result on click', async () => {
    runMock.mockResolvedValue(
      makeAgentResponse({
        tool_calls: [
          makeToolCall('list_documents', { arguments: {} }),
          makeToolCall('search_documents', { is_error: true, result: 'top_k must be between 1 and 10.' }),
        ],
      }),
    )
    const user = userEvent.setup()
    render(<AgentPage />)

    await user.type(screen.getByRole('textbox'), 'Overview?{Enter}')

    const list = await screen.findByRole('list', { name: 'Tool calls' })
    expect(within(list).getByText('list_documents')).toBeInTheDocument()
    expect(within(list).getByText('error')).toBeInTheDocument()
    expect(within(list).getAllByText('automatic (read-only)')).toHaveLength(2)

    await user.click(within(list).getByText('search_documents'))
    expect(screen.getByText('top_k must be between 1 and 10.')).toBeInTheDocument()
  })

  it('pauses for approval and continues after the user approves', async () => {
    runMock.mockResolvedValue(
      makeAgentResponse({
        status: 'needs_approval',
        run_id: 'run-1',
        answer: '',
        tool_calls: [makeToolCall('list_documents', { arguments: {} })],
        pending: [makePending('d1', 'delete_document', true)],
      }),
    )
    decideMock.mockResolvedValue(
      makeAgentResponse({
        answer: 'The handbook was deleted.',
        tool_calls: [
          makeToolCall('list_documents', { arguments: {} }),
          makeToolCall('delete_document', { approval: 'approved', result: '{"ok": true}' }),
        ],
      }),
    )
    const user = userEvent.setup()
    render(<AgentPage />)

    await user.type(screen.getByRole('textbox'), 'Delete the handbook{Enter}')
    const card = await screen.findByRole('region', { name: 'Approval needed' })
    expect(within(card).getByText(/cannot be undone/)).toBeInTheDocument()
    expect(screen.queryByText('The handbook was deleted.')).not.toBeInTheDocument()

    await user.click(within(card).getByRole('button', { name: 'Approve delete_document' }))

    expect(decideMock).toHaveBeenCalledWith('run-1', { d1: true })
    expect(await screen.findByText('The handbook was deleted.')).toBeInTheDocument()
    expect(screen.getByText('approved by you')).toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Approval needed' })).not.toBeInTheDocument()
  })
})
