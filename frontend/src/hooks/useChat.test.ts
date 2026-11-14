import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ChatApiError, sendChat } from '../services/chatApi'
import { useChat } from './useChat'

// Replace the real API module with a fake one: hook tests must never hit the network.
// `importOriginal` keeps the real ChatApiError class; only sendChat becomes a mock.
vi.mock('../services/chatApi', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../services/chatApi')>()),
  sendChat: vi.fn(),
}))
const sendChatMock = vi.mocked(sendChat)

describe('useChat', () => {
  beforeEach(() => {
    sendChatMock.mockReset()
  })

  it('starts empty, not loading, without error', () => {
    const { result } = renderHook(() => useChat())

    expect(result.current.messages).toEqual([])
    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBeNull()
    expect(result.current.lastExchange).toBeNull()
  })

  it('records the last exchange on success', async () => {
    sendChatMock.mockResolvedValue({
      reply: 'Hi',
      model: 'gemini-test',
      usage: { input_tokens: 5, output_tokens: 2, thinking_tokens: 0, total_tokens: 7 },
    })
    const { result } = renderHook(() => useChat())

    await act(async () => {
      await result.current.sendMessage('Hello')
    })

    const exchange = result.current.lastExchange
    expect(exchange?.sentMessages).toEqual([{ role: 'user', content: 'Hello' }])
    expect(exchange?.response?.model).toBe('gemini-test')
    expect(exchange?.response?.usage?.total_tokens).toBe(7)
    expect(exchange?.error).toBeNull()
    expect(exchange?.durationMs).toBeGreaterThanOrEqual(0)
  })

  it('records the last exchange on failure', async () => {
    sendChatMock.mockRejectedValue(new ChatApiError('Busy', 503))
    const { result } = renderHook(() => useChat())

    await act(async () => {
      await result.current.sendMessage('Hello')
    })

    const exchange = result.current.lastExchange
    expect(exchange?.sentMessages).toEqual([{ role: 'user', content: 'Hello' }])
    expect(exchange?.response).toBeNull()
    expect(exchange?.error).toEqual({ message: 'Busy', status: 503 })
  })

  it('shows the user message immediately, then the AI reply', async () => {
    sendChatMock.mockResolvedValue({ reply: 'A token is a piece of text.', model: 'm', usage: null })
    const { result } = renderHook(() => useChat())

    await act(async () => {
      await result.current.sendMessage('  What is a token?  ')
    })

    expect(result.current.messages).toHaveLength(2)
    expect(result.current.messages[0]).toMatchObject({ role: 'user', content: 'What is a token?' })
    expect(result.current.messages[1]).toMatchObject({
      role: 'assistant',
      content: 'A token is a piece of text.',
    })
    expect(result.current.isLoading).toBe(false)
  })

  it('sends the whole conversation (without ids) every time', async () => {
    sendChatMock
      .mockResolvedValueOnce({ reply: 'First answer', model: 'm', usage: null })
      .mockResolvedValueOnce({ reply: 'Second answer', model: 'm', usage: null })
    const { result } = renderHook(() => useChat())

    await act(async () => {
      await result.current.sendMessage('First question')
    })
    await act(async () => {
      await result.current.sendMessage('Second question')
    })

    expect(sendChatMock).toHaveBeenLastCalledWith([
      { role: 'user', content: 'First question' },
      { role: 'assistant', content: 'First answer' },
      { role: 'user', content: 'Second question' },
    ])
  })

  it('is loading while waiting for the backend', async () => {
    let finish!: (value: Awaited<ReturnType<typeof sendChat>>) => void
    sendChatMock.mockReturnValue(new Promise((resolve) => (finish = resolve)))
    const { result } = renderHook(() => useChat())

    let pending!: Promise<void>
    act(() => {
      pending = result.current.sendMessage('Hi')
    })
    expect(result.current.isLoading).toBe(true)

    await act(async () => {
      finish({ reply: 'Hello!', model: 'm', usage: null })
      await pending
    })
    expect(result.current.isLoading).toBe(false)
  })

  it('shows the API error message and keeps the user message', async () => {
    sendChatMock.mockRejectedValue(new ChatApiError('Free-tier quota used up.', 429))
    const { result } = renderHook(() => useChat())

    await act(async () => {
      await result.current.sendMessage('Hi')
    })

    expect(result.current.error).toBe('Free-tier quota used up.')
    expect(result.current.messages).toHaveLength(1)
    expect(result.current.isLoading).toBe(false)
  })

  it('clears the old error when a new message is sent', async () => {
    sendChatMock
      .mockRejectedValueOnce(new ChatApiError('Temporary problem.', 503))
      .mockResolvedValueOnce({ reply: 'Works now', model: 'm', usage: null })
    const { result } = renderHook(() => useChat())

    await act(async () => {
      await result.current.sendMessage('Try 1')
    })
    expect(result.current.error).toBe('Temporary problem.')

    await act(async () => {
      await result.current.sendMessage('Try 2')
    })
    expect(result.current.error).toBeNull()
  })

  it('ignores empty messages', async () => {
    const { result } = renderHook(() => useChat())

    await act(async () => {
      await result.current.sendMessage('   ')
    })

    expect(result.current.messages).toEqual([])
    expect(sendChatMock).not.toHaveBeenCalled()
  })
})
