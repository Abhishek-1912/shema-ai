import { useState } from 'react'
import type { ToolCall } from '../../types/agent'

const APPROVAL_LABEL: Record<ToolCall['approval'], { text: string; style: string }> = {
  auto: { text: 'automatic (read-only)', style: 'bg-slate-100 text-slate-600' },
  approved: { text: 'approved by you', style: 'bg-green-100 text-green-800' },
  rejected: { text: 'rejected by you', style: 'bg-amber-100 text-amber-800' },
}

// Pretty-print JSON results; leave plain text as it is.
function formatResult(result: string): string {
  try {
    return JSON.stringify(JSON.parse(result), null, 2)
  } catch {
    return result
  }
}

function ToolCallRow({ call, number }: { call: ToolCall; number: number }) {
  const [open, setOpen] = useState(false)
  const label = APPROVAL_LABEL[call.approval]

  return (
    <li className={`rounded-lg border p-3 text-sm ${call.is_error ? 'border-red-200 bg-red-50' : 'border-slate-200 bg-white'}`}>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex w-full flex-wrap items-center gap-2 text-left"
      >
        <span className="text-xs text-slate-400">{number}</span>
        <code className="font-semibold">{call.name}</code>
        <code className="min-w-0 flex-1 truncate text-xs text-slate-500">{JSON.stringify(call.arguments)}</code>
        <span className={`rounded px-1.5 text-xs ${label.style}`}>{label.text}</span>
        {call.is_error && <span className="rounded bg-red-100 px-1.5 text-xs text-red-700">error</span>}
        <span className="text-xs text-slate-400">{Math.round(call.duration_ms)} ms</span>
      </button>
      {open && (
        <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-xs text-slate-700">
          {formatResult(call.result)}
        </pre>
      )}
    </li>
  )
}

// Everything the AI did, in order. Click a call to see what the tool returned.
function ToolCallList({ calls }: { calls: ToolCall[] }) {
  if (calls.length === 0) return null
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        Tool calls ({calls.length})
      </h3>
      <ol aria-label="Tool calls" className="space-y-2">
        {calls.map((call, index) => (
          // The list only ever grows at the end, so the index is a stable key.
          <ToolCallRow key={index} call={call} number={index + 1} />
        ))}
      </ol>
    </div>
  )
}

export default ToolCallList
