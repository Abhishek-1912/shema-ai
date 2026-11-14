import { useEffect, useRef } from 'react'
import type { DisplayMessage } from '../types/chat'
import MessageBubble from './MessageBubble'

interface MessageListProps {
  messages: DisplayMessage[]
  isLoading: boolean
  isLoadingConversation?: boolean
  error: string | null
}

function MessageList({ messages, isLoading, isLoadingConversation = false, error }: MessageListProps) {
  // A ref points at a real DOM element: here, an invisible marker below the last message.
  const bottomRef = useRef<HTMLDivElement>(null)

  // Runs after React has drawn the screen, every time `messages` or `isLoading` changes.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading, error])

  return (
    <main className="flex-1 space-y-4 overflow-y-auto p-6">
      {isLoadingConversation && (
        <p className="mt-20 text-center text-slate-400">Loading conversation…</p>
      )}

      {messages.length === 0 && !isLoadingConversation && (
        <p className="mt-20 text-center text-slate-400">
          Start the conversation by typing a question below.
        </p>
      )}

      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}

      {isLoading && (
        <p className="text-sm text-slate-400">Shema AI is thinking…</p>
      )}

      {error && (
        <p
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700"
        >
          {error}
        </p>
      )}

      <div ref={bottomRef} />
    </main>
  )
}

export default MessageList
