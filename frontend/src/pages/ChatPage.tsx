import { useState } from 'react'
import ChatInput from '../components/ChatInput'
import MessageList from '../components/MessageList'
import UnderTheHoodPanel from '../components/UnderTheHoodPanel'
import { useChatContext } from '../context/useChatContext'

function ChatPage() {
  // The chat itself lives in ChatProvider (above the tabs), so it survives tab switches.
  const { messages, isLoading, error, lastExchange, sendMessage } = useChatContext()
  // Only a UI detail, so plain local state is fine here.
  const [showPanel, setShowPanel] = useState(true)

  return (
    <div className="flex min-w-0 flex-1">
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
          <div>
            <h1 className="text-lg font-semibold">LLM Chat</h1>
            <p className="text-xs text-slate-500">Talk to the language model directly.</p>
          </div>
          <button
            type="button"
            onClick={() => setShowPanel((shown) => !shown)}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50"
          >
            {showPanel ? 'Hide under the hood' : 'Show under the hood'}
          </button>
        </header>

        <MessageList messages={messages} isLoading={isLoading} error={error} />
        <ChatInput onSend={sendMessage} disabled={isLoading} />
      </div>

      {showPanel && <UnderTheHoodPanel lastExchange={lastExchange} />}
    </div>
  )
}

export default ChatPage
