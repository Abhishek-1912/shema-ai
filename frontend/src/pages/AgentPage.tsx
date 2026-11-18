import { useEffect, useRef } from 'react'
import ChatInput from '../components/ChatInput'
import AgentResultCard from '../components/agent/AgentResultCard'
import { useAgent } from '../hooks/useAgent'

const EXAMPLES = [
  'Which documents do we have, and how long is paternity leave?',
  'What is Project KESTREL and which form do I use to buy a monitor?',
  "Save a note called 'Parking reminder': visitor parking must be booked a day ahead.",
]

// Module 05: the AI uses MCP tools by itself; actions that change data need approval.
function AgentPage() {
  const { items, isBusy, ask, decide } = useAgent()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [items])

  return (
    <div className="flex min-w-0 flex-1 flex-col">
      <header className="border-b border-slate-200 bg-white px-6 py-3">
        <h1 className="text-lg font-semibold">Agent with tools (MCP)</h1>
        <p className="text-xs text-slate-500">
          The AI decides which tools to use. Read-only tools run automatically; anything that
          changes data waits for your approval.
        </p>
      </header>

      <main className="flex-1 space-y-6 overflow-y-auto p-6">
        {items.length === 0 && (
          <div className="mx-auto mt-16 max-w-xl text-center">
            <p className="mb-4 text-slate-400">Try one of these:</p>
            <ul className="space-y-2">
              {EXAMPLES.map((example) => (
                <li key={example}>
                  <button
                    type="button"
                    onClick={() => void ask(example)}
                    className="w-full rounded-lg border border-slate-200 bg-white px-4 py-2 text-left text-sm hover:border-blue-400"
                  >
                    {example}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
        {items.map((item) => (
          <AgentResultCard key={item.id} item={item} onDecide={(d) => void decide(item.id, d)} />
        ))}
        <div ref={bottomRef} />
      </main>

      <ChatInput
        onSend={(text) => void ask(text)}
        disabled={isBusy}
        placeholder="Ask the agent… it can search documents, list conversations, save or delete notes"
      />
    </div>
  )
}

export default AgentPage
