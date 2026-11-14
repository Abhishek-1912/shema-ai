import { useState } from 'react'

interface ChatInputProps {
  onSend: (text: string) => void
  disabled: boolean
}

function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [text, setText] = useState('')
  const canSend = text.trim().length > 0 && !disabled

  function submit() {
    if (!canSend) return
    onSend(text)
    setText('')
  }

  return (
    <form
      className="flex gap-2 border-t border-slate-200 bg-white p-4"
      onSubmit={(event) => {
        event.preventDefault()
        submit()
      }}
    >
      <textarea
        className="flex-1 resize-none rounded-xl border border-slate-300 px-4 py-2 focus:border-blue-500 focus:outline-none"
        rows={2}
        placeholder="Ask Shema AI something… (Enter to send, Shift+Enter for a new line)"
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault()
            submit()
          }
        }}
      />
      <button
        type="submit"
        disabled={!canSend}
        className="rounded-xl bg-blue-600 px-5 font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
      >
        Send
      </button>
    </form>
  )
}

export default ChatInput
