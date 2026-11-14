import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  ChatApiError,
  deleteConversation,
  getConversation,
  listConversations,
  sendChat,
} from '../services/chatApi'
import { makeChatResponse, makeMessage, makeSummary } from '../test/fixtures'
import { useChat } from './useChat'

// Replace the real API module with a fake one: hook tests must never hit the network.
// `importOriginal` keeps the real ChatApiError class; only the functions become mocks.
vi.mock('../services/chatApi', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../services/chatApi')>()),
  sendChat: vi.fn(),
  listConversations: vi.fn(),
  getConversation: vi.fn(),
  deleteConversation: vi.fn(),
}))
const sendChatMock = vi.mocked(sendChat)
const listMock = vi.mocked(listConversations)
const getMock = vi.mocked(getConversation)
const deleteMock = vi.mocked(deleteConversation)

// Render the hook and wait until the initial "load the sidebar list" request is done.
async function renderChat() {
  const hook = renderHook(() => useChat())
  await waitFor(() => expect(listMock).toHaveBeenCalled())
  return hook
}

describe('useChat', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    listMock.mockResolvedValue({ conversations: [] })
  })

  // --- Starting state ---------------------------------------------------------

  it('starts as an empty new chat and loads the conversation list', async () => {
    listMock.mockResolvedValue({ conversations: [makeSummary('c1', 'Old chat')] })
    const { result } = await renderChat()

    expect(result.current.conversationId).toBeNull()
    expect(result.current.messages).toEqual([])
    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBeNull()
    expect(result.current.lastExchange).toBeNull()
    await waitFor(() => expect(result.current.conversations).toHaveLength(1))
  })

  // --- Sending ------------------------------------------------------------------

  it('sends only the new message and null conversation_id for a new chat', async () => {
    sendChatMock.mockResolvedValue(makeChatResponse('conv-1', 'Hello', 'Hi!'))
    const { result } = await renderChat()

    let returnedId: string | null = null
    await act(async () => {
      returnedId = await result.current.sendMessage('  Hello  ')
    })

    expect(sendChatMock).toHaveBeenCalledWith({ conversation_id: null, message: 'Hello' })
    expect(returnedId).toBe('conv-1')
    expect(result.current.conversationId).toBe('conv-1')
  })

  it('sends the conversation_id with the next message', async () => {
    sendChatMock
      .mockResolvedValueOnce(makeChatResponse('conv-1', 'First', 'Answer 1'))
      .mockResolvedValueOnce(makeChatResponse('conv-1', 'Second', 'Answer 2'))
    const { result } = await renderChat()

    await act(async () => {
      await result.current.sendMessage('First')
    })
    await act(async () => {
      await result.current.sendMessage('Second')
    })

    expect(sendChatMock).toHaveBeenLastCalledWith({ conversation_id: 'conv-1', message: 'Second' })
    expect(result.current.messages.map((m) => m.content)).toEqual([
      'First',
      'Answer 1',
      'Second',
      'Answer 2',
    ])
  })

  it('shows the question immediately as "sending", then replaces it with the saved one', async () => {
    let finish!: (value: Awaited<ReturnType<typeof sendChat>>) => void
    sendChatMock.mockReturnValue(new Promise((resolve) => (finish = resolve)))
    const { result } = await renderChat()

    let pending!: Promise<string | null>
    act(() => {
      pending = result.current.sendMessage('Hi')
    })
    expect(result.current.isLoading).toBe(true)
    expect(result.current.messages).toHaveLength(1)
    expect(result.current.messages[0]).toMatchObject({ content: 'Hi', status: 'sending' })

    const response = makeChatResponse('conv-1', 'Hi', 'Hello!')
    await act(async () => {
      finish(response)
      await pending
    })

    expect(result.current.isLoading).toBe(false)
    expect(result.current.messages).toEqual([response.user_message, response.assistant_message])
  })

  it('refreshes the conversation list after a reply', async () => {
    sendChatMock.mockResolvedValue(makeChatResponse('conv-1', 'Hi', 'Hello'))
    const { result } = await renderChat()

    await act(async () => {
      await result.current.sendMessage('Hi')
    })

    expect(listMock).toHaveBeenCalledTimes(2) // once at start, once after the reply
  })

  it('records the last exchange with the history count', async () => {
    sendChatMock
      .mockResolvedValueOnce(makeChatResponse('conv-1', 'First', 'Answer 1'))
      .mockResolvedValueOnce(makeChatResponse('conv-1', 'Second', 'Answer 2'))
    const { result } = await renderChat()

    await act(async () => {
      await result.current.sendMessage('First')
    })
    expect(result.current.lastExchange?.historyCount).toBe(0)

    await act(async () => {
      await result.current.sendMessage('Second')
    })
    const exchange = result.current.lastExchange
    expect(exchange?.request).toEqual({ conversation_id: 'conv-1', message: 'Second' })
    expect(exchange?.historyCount).toBe(2)
    expect(exchange?.response?.assistant_message.content).toBe('Answer 2')
    expect(exchange?.error).toBeNull()
    expect(exchange?.durationMs).toBeGreaterThanOrEqual(0)
  })

  // --- Failures -------------------------------------------------------------------

  it('marks the question as failed and shows the error', async () => {
    sendChatMock.mockRejectedValue(new ChatApiError('Free-tier quota used up.', 429))
    const { result } = await renderChat()

    let returnedId: string | null = 'not-null'
    await act(async () => {
      returnedId = await result.current.sendMessage('Hi')
    })

    expect(returnedId).toBeNull()
    expect(result.current.error).toBe('Free-tier quota used up.')
    expect(result.current.messages).toHaveLength(1)
    expect(result.current.messages[0].status).toBe('failed')
    expect(result.current.lastExchange?.error).toEqual({ message: 'Free-tier quota used up.', status: 429 })
    expect(result.current.isLoading).toBe(false)
  })

  it('does not count failed messages as history', async () => {
    sendChatMock
      .mockRejectedValueOnce(new ChatApiError('Busy', 503))
      .mockResolvedValueOnce(makeChatResponse('conv-1', 'Try 2', 'Works now'))
    const { result } = await renderChat()

    await act(async () => {
      await result.current.sendMessage('Try 1')
    })
    await act(async () => {
      await result.current.sendMessage('Try 2')
    })

    expect(result.current.error).toBeNull()
    expect(result.current.lastExchange?.historyCount).toBe(0)
  })

  it('ignores empty messages', async () => {
    const { result } = await renderChat()

    await act(async () => {
      await result.current.sendMessage('   ')
    })

    expect(result.current.messages).toEqual([])
    expect(sendChatMock).not.toHaveBeenCalled()
  })

  // --- Opening conversations --------------------------------------------------------

  it('opens a saved conversation and loads its messages', async () => {
    const saved = [makeMessage('user', 'Old question'), makeMessage('assistant', 'Old answer')]
    getMock.mockResolvedValue({ ...makeSummary('c1', 'Old chat'), messages: saved })
    const { result } = await renderChat()

    await act(async () => {
      await result.current.openConversation('c1')
    })

    expect(getMock).toHaveBeenCalledWith('c1')
    expect(result.current.conversationId).toBe('c1')
    expect(result.current.messages).toEqual(saved)
    expect(result.current.isLoadingConversation).toBe(false)
  })

  it('does not reload the conversation that is already open', async () => {
    sendChatMock.mockResolvedValue(makeChatResponse('conv-1', 'Hi', 'Hello'))
    const { result } = await renderChat()
    await act(async () => {
      await result.current.sendMessage('Hi')
    })

    await act(async () => {
      await result.current.openConversation('conv-1')
    })

    expect(getMock).not.toHaveBeenCalled()
  })

  it('opening null starts a new empty chat', async () => {
    getMock.mockResolvedValue({ ...makeSummary('c1', 'Old'), messages: [makeMessage('user', 'x')] })
    const { result } = await renderChat()
    await act(async () => {
      await result.current.openConversation('c1')
    })

    await act(async () => {
      await result.current.openConversation(null)
    })

    expect(result.current.conversationId).toBeNull()
    expect(result.current.messages).toEqual([])
  })

  it('ignores a slow load if another conversation was opened meanwhile', async () => {
    let finishSlow!: (value: Awaited<ReturnType<typeof getConversation>>) => void
    getMock
      .mockReturnValueOnce(new Promise((resolve) => (finishSlow = resolve)))
      .mockResolvedValueOnce({ ...makeSummary('c2', 'Fast'), messages: [makeMessage('user', 'Fast chat')] })
    const { result } = await renderChat()

    let slow!: Promise<void>
    act(() => {
      slow = result.current.openConversation('c1')
    })
    await act(async () => {
      await result.current.openConversation('c2')
    })
    await act(async () => {
      finishSlow({ ...makeSummary('c1', 'Slow'), messages: [makeMessage('user', 'Slow chat')] })
      await slow
    })

    expect(result.current.conversationId).toBe('c2')
    expect(result.current.messages.map((m) => m.content)).toEqual(['Fast chat'])
  })

  it('shows an error when a conversation cannot be loaded', async () => {
    getMock.mockRejectedValue(new ChatApiError('Conversation not found.', 404))
    const { result } = await renderChat()

    await act(async () => {
      await result.current.openConversation('missing')
    })

    expect(result.current.error).toBe('Conversation not found.')
    expect(result.current.messages).toEqual([])
  })

  // --- Deleting ------------------------------------------------------------------------

  it('deletes the open conversation and resets to a new chat', async () => {
    listMock.mockResolvedValue({ conversations: [makeSummary('c1', 'Doomed')] })
    getMock.mockResolvedValue({ ...makeSummary('c1', 'Doomed'), messages: [makeMessage('user', 'x')] })
    deleteMock.mockResolvedValue(undefined)
    const { result } = await renderChat()
    await act(async () => {
      await result.current.openConversation('c1')
    })

    let deleted = false
    await act(async () => {
      deleted = await result.current.deleteConversation('c1')
    })

    expect(deleted).toBe(true)
    expect(deleteMock).toHaveBeenCalledWith('c1')
    expect(result.current.conversations).toEqual([])
    expect(result.current.conversationId).toBeNull()
    expect(result.current.messages).toEqual([])
  })

  it('keeps everything when the delete fails', async () => {
    listMock.mockResolvedValue({ conversations: [makeSummary('c1', 'Keep me')] })
    deleteMock.mockRejectedValue(new ChatApiError('Could not reach the database.', 503))
    const { result } = await renderChat()
    await waitFor(() => expect(result.current.conversations).toHaveLength(1))

    let deleted = true
    await act(async () => {
      deleted = await result.current.deleteConversation('c1')
    })

    expect(deleted).toBe(false)
    expect(result.current.conversations).toHaveLength(1)
    expect(result.current.error).toBe('Could not reach the database.')
  })
})
