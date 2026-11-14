import { useContext } from 'react'
import { ChatContext, type ChatContextValue } from './chatContextValue'

// Any component inside <ChatProvider> calls this to get the shared chat.
export function useChatContext(): ChatContextValue {
  const chat = useContext(ChatContext)
  if (chat === null) {
    throw new Error('useChatContext must be used inside <ChatProvider>')
  }
  return chat
}
