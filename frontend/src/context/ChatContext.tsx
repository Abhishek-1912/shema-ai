import type { ReactNode } from 'react'
import { useChat } from '../hooks/useChat'
import { ChatContext } from './chatContextValue'

// Creates ONE chat and shares it with everything inside. Because it sits above the
// tabs, switching tabs does not destroy it, so the conversation survives.
export function ChatProvider({ children }: { children: ReactNode }) {
  const chat = useChat()
  return <ChatContext.Provider value={chat}>{children}</ChatContext.Provider>
}
