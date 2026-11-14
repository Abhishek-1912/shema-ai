import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import ChatInput from '../components/ChatInput'
import ConversationList from '../components/ConversationList'
import MessageList from '../components/MessageList'
import UnderTheHoodPanel from '../components/UnderTheHoodPanel'
import { useChatContext } from '../context/useChatContext'

function ChatPage() {
  // The chat itself lives in ChatProvider (above the tabs), so it survives tab switches.
  const {
    conversations,
    messages,
    isLoading,
    isLoadingConversation,
    error,
    lastExchange,
    sendMessage,
    openConversation,
    deleteConversation,
  } = useChatContext()
  // Only a UI detail, so plain local state is fine here.
  const [showPanel, setShowPanel] = useState(true)

  // The URL decides which conversation is shown: /chat = new chat, /chat/<id> = saved chat.
  const { conversationId: routeId } = useParams()
  const navigate = useNavigate()

  useEffect(() => {
    void openConversation(routeId ?? null)
  }, [routeId, openConversation])

  async function handleSend(text: string) {
    const savedId = await sendMessage(text)
    // A brand-new chat just got its ID from the backend: put it in the URL.
    if (savedId && savedId !== routeId) {
      navigate(`/chat/${savedId}`, { replace: true })
    }
  }

  async function handleDelete(id: string) {
    const deleted = await deleteConversation(id)
    if (deleted && id === routeId) {
      navigate('/chat', { replace: true })
    }
  }

  return (
    <div className="flex min-w-0 flex-1">
      <ConversationList conversations={conversations} onDelete={handleDelete} />

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
          <div>
            <h1 className="text-lg font-semibold">LLM Chat</h1>
            <p className="text-xs text-slate-500">
              Talk to the language model. Chats are saved in the database.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setShowPanel((shown) => !shown)}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50"
          >
            {showPanel ? 'Hide under the hood' : 'Show under the hood'}
          </button>
        </header>

        <MessageList
          messages={messages}
          isLoading={isLoading}
          isLoadingConversation={isLoadingConversation}
          error={error}
        />
        <ChatInput onSend={handleSend} disabled={isLoading || isLoadingConversation} />
      </div>

      {showPanel && <UnderTheHoodPanel lastExchange={lastExchange} />}
    </div>
  )
}

export default ChatPage
