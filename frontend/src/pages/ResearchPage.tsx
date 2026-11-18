import { useEffect, useRef } from 'react'
import ChatInput from '../components/ChatInput'
import ResearchResultCard from '../components/research/ResearchResultCard'
import { useResearch } from '../hooks/useResearch'

const EXAMPLES = [
  'Give me an overview for a new employee: parental leave for fathers and mothers, what Project KESTREL is, and whether there is a company gym.',
  'Which documents do we have, and what do they say about buying equipment and security rules?',
]

// Module 07: several agents on one question — split, research in parallel, write up.
function ResearchPage() {
  const { items, isBusy, ask } = useResearch()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [items])

  return (
    <div className="flex min-w-0 flex-1 flex-col">
      <header className="border-b border-slate-200 bg-white px-6 py-3">
        <h1 className="text-lg font-semibold">Research agent</h1>
        <p className="text-xs text-slate-500">
          A coordinator splits your question, researchers search the documents in parallel
          (read-only: they can never change data), and a writer combines their findings.
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
          <ResearchResultCard key={item.id} item={item} />
        ))}
        <div ref={bottomRef} />
      </main>

      <ChatInput
        onSend={(text) => void ask(text)}
        disabled={isBusy}
        placeholder="Ask a broad question with several parts…"
      />
    </div>
  )
}

export default ResearchPage
