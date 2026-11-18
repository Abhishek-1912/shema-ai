import { useEffect, useRef } from 'react'
import ChatInput from '../components/ChatInput'
import AskResultCard from '../components/rag/AskResultCard'
import DocumentList from '../components/rag/DocumentList'
import DocumentUploader from '../components/rag/DocumentUploader'
import { useAsk } from '../hooks/useAsk'
import { useDocuments } from '../hooks/useDocuments'

// Module 04: upload documents on the left, ask questions about them on the right.
function RagPage() {
  const { documents, isLoading, isUploading, error, notice, upload, remove } = useDocuments()
  const { items, isAsking, ask } = useAsk()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [items])

  return (
    <div className="flex min-w-0 flex-1">
      <section
        aria-label="Your documents"
        className="flex w-80 shrink-0 flex-col gap-4 overflow-y-auto border-r border-slate-200 bg-white p-4"
      >
        <div>
          <h2 className="font-semibold">Your documents</h2>
          <p className="text-xs text-slate-500">The AI answers only from these.</p>
        </div>

        <DocumentUploader onUpload={upload} isUploading={isUploading} />

        {notice && (
          <p role="status" className="rounded-lg bg-green-50 px-3 py-2 text-sm text-green-800">
            {notice}
          </p>
        )}
        {error && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <DocumentList documents={documents} isLoading={isLoading} onDelete={(id) => void remove(id)} />
      </section>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-b border-slate-200 bg-white px-6 py-3">
          <h1 className="text-lg font-semibold">Ask your documents</h1>
          <p className="text-xs text-slate-500">
            Answers come only from your documents. Click a number like{' '}
            <span className="rounded bg-blue-100 px-1 text-blue-700">1</span> to see the source.
          </p>
        </header>

        <main className="flex-1 space-y-6 overflow-y-auto p-6">
          {items.length === 0 && (
            <p className="mt-20 text-center text-slate-400">
              {documents.length === 0
                ? 'Upload a document on the left, then ask a question about it.'
                : 'Ask a question about your documents below.'}
            </p>
          )}
          {items.map((item) => (
            <AskResultCard key={item.id} item={item} />
          ))}
          <div ref={bottomRef} />
        </main>

        <ChatInput
          onSend={(text) => void ask(text)}
          disabled={isAsking}
          placeholder="Ask a question about your documents… (Enter to send)"
        />
      </div>
    </div>
  )
}

export default RagPage
