import { createContext } from 'react'
import type { useChat } from '../hooks/useChat'

// The type of what the context holds: exactly what useChat() returns.
export type ChatContextValue = ReturnType<typeof useChat>

// The "channel" itself. null = no ChatProvider above us.
export const ChatContext = createContext<ChatContextValue | null>(null)
