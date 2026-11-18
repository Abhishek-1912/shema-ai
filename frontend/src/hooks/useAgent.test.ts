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

    expect(runMock).toHaveBeenCalledWith('Paternity leave?', null) // first question: new session
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

  it('sends follow-up questions in the same session (memory)', async () => {
    runMock.mockResolvedValue(makeAgentResponse({ session_id: 'session-1' }))
    const { result } = renderHook(() => useAgent())

    await act(async () => {
      await result.current.ask('Paternity leave?')
    })
    await act(async () => {
      await result.current.ask('And for mothers?')
    })

    expect(runMock).toHaveBeenLastCalledWith('And for mothers?', 'session-1')
    expect(result.current.sessionId).toBe('session-1')
  })

  it('starts a new session: clears the questions and forgets the session', async () => {
    runMock.mockResolvedValue(makeAgentResponse({ session_id: 'session-1' }))
    const { result } = renderHook(() => useAgent())
    await act(async () => {
      await result.current.ask('Paternity leave?')
    })

    act(() => result.current.newSession())
    await act(async () => {
      await result.current.ask('Hello')
    })

    expect(runMock).toHaveBeenLastCalledWith('Hello', null)
    expect(result.current.items.map((i) => i.question)).toEqual(['Hello'])
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
