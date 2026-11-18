import type { DocumentSummary } from '../../types/documents'

interface DocumentListProps {
  documents: DocumentSummary[]
  isLoading: boolean
  onDelete: (id: string) => void
}

const TYPE_LABEL: Record<DocumentSummary['source_type'], string> = {
  pdf: 'PDF',
  docx: 'Word',
  txt: 'TXT',
  md: 'MD',
  text: 'Text',
}

function DocumentList({ documents, isLoading, onDelete }: DocumentListProps) {
  if (isLoading) return <p className="text-sm text-slate-400">Loading documents…</p>
  if (documents.length === 0) {
    return <p className="text-sm text-slate-400">No documents yet. Upload one to start asking.</p>
  }

  return (
    <ul aria-label="Documents" className="space-y-1">
      {documents.map((document) => (
        <li key={document.id} className="group flex items-start gap-2 rounded-lg px-2 py-2 hover:bg-slate-50">
          <span className="mt-0.5 rounded bg-slate-100 px-1.5 text-xs font-medium text-slate-600">
            {TYPE_LABEL[document.source_type]}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium" title={document.title}>
              {document.title}
            </p>
            <p className="text-xs text-slate-500">
              {document.chunk_count} {document.chunk_count === 1 ? 'chunk' : 'chunks'}
            </p>
          </div>
          <button
            type="button"
            aria-label={`Delete document "${document.title}"`}
            onClick={() => {
              if (window.confirm(`Delete "${document.title}"? It will no longer be searchable.`)) {
                onDelete(document.id)
              }
            }}
            className="rounded px-2 text-slate-400 opacity-0 hover:bg-red-50 hover:text-red-600 focus:opacity-100 group-hover:opacity-100"
          >
            ×
          </button>
        </li>
      ))}
    </ul>
  )
}

export default DocumentList
