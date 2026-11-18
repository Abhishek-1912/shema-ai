import { useState } from 'react'
import type { PendingCall } from '../../types/agent'

interface ApprovalCardProps {
  pending: PendingCall[]
  disabled: boolean
  onDecide: (decisions: Record<string, boolean>) => void
}

// The AI wants to change data. Nothing happens until the user approves or rejects
// EVERY pending action; the decisions are sent together.
function ApprovalCard({ pending, disabled, onDecide }: ApprovalCardProps) {
  const [decisions, setDecisions] = useState<Record<string, boolean>>({})

  function choose(callId: string, approve: boolean) {
    const next = { ...decisions, [callId]: approve }
    setDecisions(next)
    if (pending.every((p) => p.call_id in next)) onDecide(next)
  }

  const anyDestructive = pending.some((p) => p.destructive)

  return (
    <section
      aria-label="Approval needed"
      className={`rounded-xl border-2 p-4 ${anyDestructive ? 'border-red-300 bg-red-50' : 'border-amber-300 bg-amber-50'}`}
    >
      <h3 className="mb-1 font-semibold">Your approval is needed</h3>
      <p className="mb-3 text-sm text-slate-600">
        The AI wants to change data. Nothing has happened yet.
      </p>
      <ul className="space-y-3">
        {pending.map((call) => {
          const decided = decisions[call.call_id]
          return (
            <li key={call.call_id} className="rounded-lg bg-white p-3 text-sm">
              <p className="mb-1">
                <code className="font-semibold">{call.name}</code>{' '}
                {call.destructive ? (
                  <span className="rounded bg-red-100 px-1.5 text-xs font-semibold text-red-700">
                    ⚠ destructive: cannot be undone
                  </span>
                ) : (
                  <span className="rounded bg-amber-100 px-1.5 text-xs text-amber-800">changes data</span>
                )}
              </p>
              <pre className="mb-2 whitespace-pre-wrap rounded bg-slate-50 p-2 text-xs">
                {JSON.stringify(call.arguments, null, 2)}
              </pre>
              {decided === undefined ? (
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={disabled}
                    onClick={() => choose(call.call_id, true)}
                    aria-label={`Approve ${call.name}`}
                    className={`rounded-lg px-3 py-1 font-medium text-white disabled:opacity-50 ${
                      call.destructive ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'
                    }`}
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    disabled={disabled}
                    onClick={() => choose(call.call_id, false)}
                    aria-label={`Reject ${call.name}`}
                    className="rounded-lg border border-slate-300 bg-white px-3 py-1 font-medium hover:bg-slate-50 disabled:opacity-50"
                  >
                    Reject
                  </button>
                </div>
              ) : (
                <p className="text-xs font-medium">{decided ? 'You approved this.' : 'You rejected this.'}</p>
              )}
            </li>
          )
        })}
      </ul>
    </section>
  )
}

export default ApprovalCard
