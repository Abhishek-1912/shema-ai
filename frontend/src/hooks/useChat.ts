import { useState } from 'react'
import { ChatApiError, sendChat } from '../services/chatApi'
import type { LastExchange, Message } from '../types/chat'

const GENERIC_ERROR = 'Something went wrong. Please try again.'

// Holds the chat's data and logic, so components only have to draw the UI.
export function useChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastExchange, setLastExchange] = useState<LastExchange | null>(null)

  async function sendMessage(text: string) {
    const trimmed = text.trim()
    if (!trimmed || isLoading) return

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: trimmed,
    }
    // The LLM has no memory, so we send the whole conversation, including the new message.
    const history = [...messages, userMessage]
    const sentMessages = history.map(({ role, content }) => ({ role, content }))

    setMessages(history)
    setError(null)
    setIsLoading(true)

    const startedAt = performance.now()
    try {
      const response = await sendChat(sentMessages)
      const reply: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: response.reply,
      }
      setMessages((prev) => [...prev, reply])
      setLastExchange({
        sentMessages,
        durationMs: performance.now() - startedAt,
        response,
        error: null,
      })
    } catch (err) {
      const apiError = err instanceof ChatApiError ? err : null
      const message = apiError ? apiError.message : GENERIC_ERROR
      setError(message)
      setLastExchange({
        sentMessages,
        durationMs: performance.now() - startedAt,
        response: null,
        error: { message, status: apiError ? apiError.status : null },
      })
    } finally {
      setIsLoading(false)
    }
  }

  return { messages, isLoading, error, lastExchange, sendMessage }
}
