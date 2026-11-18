import { useState } from 'react'
import type { AskItem } from '../../types/documents'
import AnswerText from './AnswerText'
import SourceList from './SourceList'

// One question with its answer and sources.
function AskResultCard({ item }: { item: AskItem }) {
  const [activeNumber, setActiveNumber] = useState<number | null>(null)
  const response = item.response

  return (
    <article className="space-y-3" aria-label={`Question: ${item.question}`}>
      <div className="flex justify-end">
        <p className="max-w-[75%] whitespace-pre-wrap rounded-2xl bg-blue-600 px-4 py-2 text-white">
          {item.question}
        </p>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4">
        {item.status === 'loading' && (
          <p className="text-sm text-slate-400">Searching your documents…</p>
        )}

        {item.status === 'error' && (
          <p role="alert" className="text-sm text-red-700">
            {item.error}
          </p>
        )}

        {response && (
          <>
            <div className={response.found ? '' : 'text-slate-500 italic'}>
              <AnswerText
                answer={response.answer}
                sources={response.sources}
                activeNumber={activeNumber}
                onCite={setActiveNumber}
              />
            </div>

            {response.sources.length > 0 && (
              <div className="mt-4">
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Sources ({response.sources.filter((s) => s.cited).length} used of{' '}
                  {response.sources.length} found)
                </h3>
                <SourceList
                  sources={response.sources}
                  activeNumber={activeNumber}
                  onSelect={setActiveNumber}
                />
              </div>
            )}

            {response.usage && (
              <p className="mt-3 text-xs text-slate-400">
                {response.model} · {response.usage.total_tokens} tokens
              </p>
            )}
          </>
        )}
      </div>
    </article>
  )
}

export default AskResultCard
