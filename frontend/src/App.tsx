import ChatInput from './components/ChatInput'
import MessageList from './components/MessageList'
import { useChat } from './hooks/useChat'

function App() {
  const { messages, isLoading, error, sendMessage } = useChat()

  return (
    <div className="flex h-screen flex-col bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white px-6 py-4">
        <h1 className="text-xl font-semibold">Shema AI</h1>
        <p className="text-sm text-slate-500">Your AI knowledge assistant</p>
      </header>

      <MessageList messages={messages} isLoading={isLoading} error={error} />

      <ChatInput onSend={sendMessage} disabled={isLoading} />
    </div>
  )
}

export default App
