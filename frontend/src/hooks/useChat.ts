import { useState } from 'react'
import { ChatApiError, sendChat } from '../services/chatApi'
import type { Message } from '../types/chat'

// Holds the chat's data and logic, so components only have to draw the UI.
export function useChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

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

    setMessages(history)
    setError(null)
    setIsLoading(true)

    try {
      const response = await sendChat(
        history.map(({ role, content }) => ({ role, content })),
      )
      const reply: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: response.reply,
      }
      setMessages((prev) => [...prev, reply])
    } catch (err) {
      setError(
        err instanceof ChatApiError
          ? err.message
          : 'Something went wrong. Please try again.',
      )
    } finally {
      setIsLoading(false)
    }
  }

  return { messages, isLoading, error, sendMessage }
}
