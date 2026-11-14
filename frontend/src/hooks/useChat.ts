import { useState } from 'react'
import type { Message } from '../types/chat'

// Holds the chat's data and logic, so components only have to draw the UI.
export function useChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)

  function sendMessage(text: string) {
    const trimmed = text.trim()
    if (!trimmed || isLoading) return

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: trimmed,
    }
    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)

    // TEMPORARY: fake AI reply. Replaced by a real backend call in the next task.
    setTimeout(() => {
      const reply: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `You said: "${trimmed}"\n(This is a fake reply. The real AI gets connected next.)`,
      }
      setMessages((prev) => [...prev, reply])
      setIsLoading(false)
    }, 800)
  }

  return { messages, isLoading, sendMessage }
}
