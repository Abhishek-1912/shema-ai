import { useEffect, useRef } from 'react'
import type { Message } from '../types/chat'
import MessageBubble from './MessageBubble'

interface MessageListProps {
  messages: Message[]
  isLoading: boolean
}

function MessageList({ messages, isLoading }: MessageListProps) {
  // A ref points at a real DOM element: here, an invisible marker below the last message.
  const bottomRef = useRef<HTMLDivElement>(null)

  // Runs after React has drawn the screen, every time `messages` or `isLoading` changes.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  return (
    <main className="flex-1 space-y-4 overflow-y-auto p-6">
      {messages.length === 0 && (
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

      <div ref={bottomRef} />
    </main>
  )
}

export default MessageList
