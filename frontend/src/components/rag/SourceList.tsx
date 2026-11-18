import { useEffect, useRef } from 'react'
import type { Source } from '../../types/documents'

interface SourceListProps {
  sources: Source[]
  activeNumber: number | null
  onSelect: (number: number | null) => void
}

function location(source: Source): string {
  return source.page_number !== null ? `page ${source.page_number}` : `part ${source.chunk_index + 1}`
}

// The chunks the AI was given. Clicking a citation in the answer opens the matching one here.
function SourceList({ sources, activeNumber, onSelect }: SourceListProps) {
  const activeRef = useRef<HTMLLIElement>(null)

  useEffect(() => {
    activeRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [activeNumber])

  return (
    <ol aria-label="Sources" className="space-y-2">
      {sources.map((source) => {
        const isActive = source.number === activeNumber
        return (
          <li
            key={source.number}
            ref={isActive ? activeRef : undefined}
            className={`rounded-lg border p-3 text-sm ${
              isActive ? 'border-blue-400 bg-blue-50' : 'border-slate-200 bg-white'
            }`}
          >
            <button
              type="button"
              aria-expanded={isActive}
              onClick={() => onSelect(isActive ? null : source.number)}
              className="flex w-full items-center gap-2 text-left"
            >
              <span className="rounded bg-slate-100 px-1.5 text-xs font-semibold text-slate-700">
                {source.number}
              </span>
              <span className="min-w-0 flex-1 truncate font-medium">{source.document_title}</span>
              <span className="text-xs text-slate-500">{location(source)}</span>
              <span
                className={`rounded px-1.5 text-xs ${
                  source.cited ? 'bg-green-100 text-green-800' : 'bg-slate-100 text-slate-500'
                }`}
              >
                {source.cited ? 'used' : 'not used'}
              </span>
            </button>
            {isActive && (
              <div className="mt-2 border-t border-blue-200 pt-2">
                <p className="whitespace-pre-wrap text-slate-700">{source.content}</p>
                <p className="mt-1 text-xs text-slate-500">
                  Similarity to your question: {source.similarity.toFixed(3)}
                </p>
              </div>
            )}
          </li>
        )
      })}
    </ol>
  )
}

export default SourceList
