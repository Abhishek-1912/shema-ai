import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { runAgent, sendDecisions } from '../services/agentApi'
import { ApiError } from '../services/http'
import { makeAgentResponse, makePending } from '../test/fixtures'
import { useAgent } from './useAgent'

vi.mock('../services/agentApi', () => ({ runAgent: vi.fn(), sendDecisions: vi.fn() }))
const runMock = vi.mocked(runAgent)
const decideMock = vi.mocked(sendDecisions)

const PAUSED = makeAgentResponse({
  status: 'needs_approval',
  run_id: 'run-1',
  answer: '',
  pending: [makePending('d1', 'delete_document', true)],
})

describe('useAgent', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('runs a question and stores the finished response', async () => {
    runMock.mockResolvedValue(makeAgentResponse())
    const { result } = renderHook(() => useAgent())

    await act(async () => {
      await result.current.ask('  Paternity leave?  ')
    })

    expect(runMock).toHaveBeenCalledWith('Paternity leave?')
    expect(result.current.items[0]).toMatchObject({ status: 'done', question: 'Paternity leave?' })
    expect(result.current.isBusy).toBe(false)
  })

  it('waits for approval, then sends the decisions for that run', async () => {
    runMock.mockResolvedValue(PAUSED)
    decideMock.mockResolvedValue(makeAgentResponse({ answer: 'Deleted.' }))
    const { result } = renderHook(() => useAgent())

    await act(async () => {
      await result.current.ask('Delete the handbook')
    })
    expect(result.current.items[0].status).toBe('needs_approval')

    await act(async () => {
      await result.current.decide(result.current.items[0].id, { d1: true })
    })

    expect(decideMock).toHaveBeenCalledWith('run-1', { d1: true })
    expect(result.current.items[0]).toMatchObject({ status: 'done' })
    expect(result.current.items[0].response?.answer).toBe('Deleted.')
  })

  it('ignores decisions for an item that is not waiting', async () => {
    runMock.mockResolvedValue(makeAgentResponse())
    const { result } = renderHook(() => useAgent())
    await act(async () => {
      await result.current.ask('Hi')
    })

    await act(async () => {
      await result.current.decide(result.current.items[0].id, { d1: true })
    })

    expect(decideMock).not.toHaveBeenCalled()
  })

  it('shows an error when the run fails', async () => {
    runMock.mockRejectedValue(new ApiError('The AI is receiving too many requests.', 429))
    const { result } = renderHook(() => useAgent())

    await act(async () => {
      await result.current.ask('Anything')
    })

    expect(result.current.items[0]).toMatchObject({ status: 'error', error: 'The AI is receiving too many requests.' })
  })

  it('ignores empty questions', async () => {
    const { result } = renderHook(() => useAgent())

    await act(async () => {
      await result.current.ask('  ')
    })

    expect(runMock).not.toHaveBeenCalled()
    expect(result.current.items).toEqual([])
  })
})
