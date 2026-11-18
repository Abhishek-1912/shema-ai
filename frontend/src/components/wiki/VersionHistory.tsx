import { useState } from 'react'
import type { ArticleVersion } from '../../types/wiki'
import MarkdownView from '../MarkdownView'

interface VersionHistoryProps {
  versions: ArticleVersion[] // newest first
  currentVersion: number
  disabled: boolean
  onRestore: (version: number) => void
}

// Every saved version. Click one to preview it; older ones can be restored
// (restoring ADDS a new version with the old text — history is never deleted).
function VersionHistory({ versions, currentVersion, disabled, onRestore }: VersionHistoryProps) {
  const [open, setOpen] = useState<number | null>(null)

  return (
    <aside aria-label="Version history" className="w-80 shrink-0 overflow-y-auto border-l border-slate-200 bg-white p-4">
      <h2 className="mb-3 font-semibold">History ({versions.length} versions)</h2>
      <ol className="space-y-2">
        {versions.map((v) => {
          const isCurrent = v.version === currentVersion
          const isOpen = open === v.version
          return (
            <li key={v.version} className={`rounded-lg border p-2 text-sm ${isOpen ? 'border-blue-300' : 'border-slate-200'}`}>
              <button
                type="button"
                aria-expanded={isOpen}
                onClick={() => setOpen(isOpen ? null : v.version)}
                className="w-full text-left"
              >
                <span className="font-medium">Version {v.version}</span>
                {isCurrent && <span className="ml-2 rounded bg-blue-100 px-1 text-xs text-blue-700">current</span>}
                {v.created_by === 'ai' && <span className="ml-2 rounded bg-purple-100 px-1 text-xs text-purple-700">AI</span>}
                <span className="block text-xs text-slate-500">
                  {new Date(v.created_at).toLocaleString()} · {v.change_note ?? 'no note'}
                </span>
              </button>
              {isOpen && (
                <div className="mt-2 border-t border-slate-200 pt-2">
                  <div className="max-h-60 overflow-y-auto text-xs">
                    <MarkdownView markdown={v.content} />
                  </div>
                  {!isCurrent && (
                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() => onRestore(v.version)}
                      className="mt-2 rounded-lg border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50 disabled:opacity-50"
                    >
                      Restore version {v.version}
                    </button>
                  )}
                </div>
              )}
            </li>
          )
        })}
      </ol>
    </aside>
  )
}

export default VersionHistory
