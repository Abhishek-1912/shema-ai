import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { askDocuments } from '../services/documentsApi'
import { ApiError } from '../services/http'
import { makeAskResponse, makeSource } from '../test/fixtures'
import { useAsk } from './useAsk'

vi.mock('../services/documentsApi', () => ({ askDocuments: vi.fn() }))
const askMock = vi.mocked(askDocuments)

describe('useAsk', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('shows the question as loading, then the answer', async () => {
    let finish!: (value: Awaited<ReturnType<typeof askDocuments>>) => void
    askMock.mockReturnValue(new Promise((resolve) => (finish = resolve)))
    const { result } = renderHook(() => useAsk())

    let pending!: Promise<void>
    act(() => {
      pending = result.current.ask('  How long can I return items?  ')
    })
    expect(result.current.isAsking).toBe(true)
    expect(result.current.items[0]).toMatchObject({ question: 'How long can I return items?', status: 'loading' })

    const response = makeAskResponse('30 days [1].', [makeSource(1)])
    await act(async () => {
      finish(response)
      await pending
    })

    expect(result.current.isAsking).toBe(false)
    expect(result.current.items[0]).toMatchObject({ status: 'done', response })
    expect(askMock).toHaveBeenCalledWith('How long can I return items?')
  })

  it('keeps earlier questions and adds new ones at the end', async () => {
    askMock.mockResolvedValue(makeAskResponse('ok', []))
    const { result } = renderHook(() => useAsk())

    await act(async () => {
      await result.current.ask('First?')
    })
    await act(async () => {
      await result.current.ask('Second?')
    })

    expect(result.current.items.map((i) => i.question)).toEqual(['First?', 'Second?'])
  })

  it('records an error for the failed question', async () => {
    askMock.mockRejectedValue(new ApiError('The AI is receiving too many requests.', 429))
    const { result } = renderHook(() => useAsk())

    await act(async () => {
      await result.current.ask('Anything?')
    })

    expect(result.current.items[0]).toMatchObject({
      status: 'error',
      error: 'The AI is receiving too many requests.',
    })
  })

  it('ignores empty questions', async () => {
    const { result } = renderHook(() => useAsk())

    await act(async () => {
      await result.current.ask('   ')
    })

    expect(result.current.items).toEqual([])
    expect(askMock).not.toHaveBeenCalled()
  })
})
