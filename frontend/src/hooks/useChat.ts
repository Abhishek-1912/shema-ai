import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ChatApiError,
  deleteConversation as apiDeleteConversation,
  getConversation,
  listConversations,
  sendChat,
} from '../services/chatApi'
import type {
  ChatRequest,
  ConversationSummary,
  DisplayMessage,
  LastExchange,
} from '../types/chat'

const GENERIC_ERROR = 'Something went wrong. Please try again.'
const MAX_HISTORY_MESSAGES = 40 // must match the backend (docs/api-contract.md)

function errorMessage(err: unknown): string {
  return err instanceof ChatApiError ? err.message : GENERIC_ERROR
}

function errorStatus(err: unknown): number | null {
  return err instanceof ChatApiError ? err.status : null
}

// Holds the chat's data and logic, so components only have to draw the UI.
// The backend owns the history: we send ONE new message plus the conversation ID.
export function useChat() {
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<DisplayMessage[]>([])
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [isLoading, setIsLoading] = useState(false) // waiting for the AI's reply
  const [isLoadingConversation, setIsLoadingConversation] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastExchange, setLastExchange] = useState<LastExchange | null>(null)

  // Refs hold the LATEST values for code that runs after an `await`
  // (state captured in a closure could be out of date by then).
  const conversationIdRef = useRef<string | null>(null)
  const loadCounterRef = useRef(0) // lets us ignore answers to outdated "open" requests

  const setCurrentConversation = useCallback((id: string | null) => {
    conversationIdRef.current = id
    setConversationId(id)
  }, [])

  const refreshConversations = useCallback(async () => {
    try {
      const data = await listConversations()
      setConversations(data.conversations)
    } catch (err) {
      setError(errorMessage(err))
    }
  }, [])

  // Load the sidebar list once, when the app starts. State is set in the promise
  // callbacks; `ignore` drops a late answer if the component is already gone.
  useEffect(() => {
    let ignore = false
    listConversations()
      .then((data) => {
        if (!ignore) setConversations(data.conversations)
      })
      .catch((err: unknown) => {
        if (!ignore) setError(errorMessage(err))
      })
    return () => {
      ignore = true
    }
  }, [])

  // Show a saved conversation (id) or an empty new chat (null).
  const openConversation = useCallback(
    async (id: string | null) => {
      if (id === conversationIdRef.current) return // already showing it

      const loadNumber = ++loadCounterRef.current
      setCurrentConversation(id)
      setMessages([])
      setError(null)
      setLastExchange(null)
      if (id === null) {
        setIsLoadingConversation(false)
        return
      }

      setIsLoadingConversation(true)
      try {
        const detail = await getConversation(id)
        if (loadNumber !== loadCounterRef.current) return // user already opened another chat
        setMessages(detail.messages)
      } catch (err) {
        if (loadNumber !== loadCounterRef.current) return
        setError(errorMessage(err))
      } finally {
        if (loadNumber === loadCounterRef.current) setIsLoadingConversation(false)
      }
    },
    [setCurrentConversation],
  )

  // Returns the conversation ID if the reply arrived (so the page can update the URL).
  async function sendMessage(text: string): Promise<string | null> {
    const trimmed = text.trim()
    if (!trimmed || isLoading) return null

    const request: ChatRequest = { conversation_id: conversationIdRef.current, message: trimmed }
    const savedCount = messages.filter((m) => m.status === undefined).length
    const historyCount = Math.min(savedCount, MAX_HISTORY_MESSAGES)

    // Show the question right away ("optimistic UI"), with a temporary ID.
    const tempId = `local-${crypto.randomUUID()}`
    setMessages((prev) => [
      ...prev,
      {
        id: tempId,
        role: 'user',
        content: trimmed,
        created_at: new Date().toISOString(),
        model: null,
        usage: null,
        status: 'sending',
      },
    ])
    setError(null)
    setIsLoading(true)

    const startedAt = performance.now()
    // Did the user stay on this conversation while we waited?
    const stillHere = () => conversationIdRef.current === request.conversation_id

    try {
      const response = await sendChat(request)
      const durationMs = performance.now() - startedAt
      setLastExchange({ request, historyCount, durationMs, response, error: null })
      void refreshConversations() // new title / new order in the sidebar

      if (!stillHere()) return null
      setCurrentConversation(response.conversation_id)
      // Replace the temporary message with the saved one, then add the reply.
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== tempId),
        response.user_message,
        response.assistant_message,
      ])
      return response.conversation_id
    } catch (err) {
      const message = errorMessage(err)
      setLastExchange({
        request,
        historyCount,
        durationMs: performance.now() - startedAt,
        response: null,
        error: { message, status: errorStatus(err) },
      })
      if (stillHere()) {
        setError(message)
        setMessages((prev) =>
          prev.map((m) => (m.id === tempId ? { ...m, status: 'failed' } : m)),
        )
      }
      return null
    } finally {
      setIsLoading(false)
    }
  }

  // Returns true if the conversation was deleted.
  async function deleteConversation(id: string): Promise<boolean> {
    try {
      await apiDeleteConversation(id)
    } catch (err) {
      setError(errorMessage(err))
      return false
    }
    setConversations((prev) => prev.filter((c) => c.id !== id))
    if (conversationIdRef.current === id) {
      loadCounterRef.current++ // cancel a load that may still be running
      setCurrentConversation(null)
      setMessages([])
      setLastExchange(null)
    }
    return true
  }

  return {
    conversationId,
    messages,
    conversations,
    isLoading,
    isLoadingConversation,
    error,
    lastExchange,
    sendMessage,
    openConversation,
    deleteConversation,
  }
}
