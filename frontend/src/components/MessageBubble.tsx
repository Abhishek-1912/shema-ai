import type { Message } from '../types/chat'

interface MessageBubbleProps {
  message: Message
}

function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[75%] whitespace-pre-wrap rounded-2xl px-4 py-2 ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'border border-slate-200 bg-white text-slate-900'
        }`}
      >
        {message.content}
      </div>
    </div>
  )
}

export default MessageBubble
