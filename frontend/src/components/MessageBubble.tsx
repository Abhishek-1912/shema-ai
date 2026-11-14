import type { DisplayMessage } from '../types/chat'

interface MessageBubbleProps {
  message: DisplayMessage
}

function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
      <div
        className={`max-w-[75%] whitespace-pre-wrap rounded-2xl px-4 py-2 ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'border border-slate-200 bg-white text-slate-900'
        } ${message.status === 'sending' ? 'opacity-60' : ''}`}
      >
        {message.content}
      </div>
      {message.status === 'failed' && (
        <p className="mt-1 text-xs text-red-600">Not sent. Nothing was saved, so try again.</p>
      )}
    </div>
  )
}

export default MessageBubble
