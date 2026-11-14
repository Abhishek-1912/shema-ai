import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useChat } from './useChat'

describe('useChat', () => {
  // Fake timers let us skip the 800ms wait instantly instead of really waiting.
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('starts with no messages and not loading', () => {
    const { result } = renderHook(() => useChat())

    expect(result.current.messages).toEqual([])
    expect(result.current.isLoading).toBe(false)
  })

  it('adds the user message, then the AI reply', () => {
    const { result } = renderHook(() => useChat())

    act(() => {
      result.current.sendMessage('  What is a token?  ')
    })

    // Right after sending: the user message (trimmed) is shown and we are waiting.
    expect(result.current.messages).toHaveLength(1)
    expect(result.current.messages[0]).toMatchObject({
      role: 'user',
      content: 'What is a token?',
    })
    expect(result.current.isLoading).toBe(true)

    // Jump 800ms forward in time: the fake reply arrives.
    act(() => {
      vi.advanceTimersByTime(800)
    })

    expect(result.current.messages).toHaveLength(2)
    expect(result.current.messages[1].role).toBe('assistant')
    expect(result.current.isLoading).toBe(false)
  })

  it('ignores empty messages', () => {
    const { result } = renderHook(() => useChat())

    act(() => {
      result.current.sendMessage('   ')
    })

    expect(result.current.messages).toEqual([])
    expect(result.current.isLoading).toBe(false)
  })

  it('gives every message a unique id', () => {
    const { result } = renderHook(() => useChat())

    act(() => {
      result.current.sendMessage('Hi')
    })
    act(() => {
      vi.advanceTimersByTime(800)
    })

    const [first, second] = result.current.messages
    expect(first.id).not.toBe(second.id)
  })
})
