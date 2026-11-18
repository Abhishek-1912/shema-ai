import type { AgentItem } from '../../types/agent'
import MarkdownView from '../MarkdownView'
import ApprovalCard from './ApprovalCard'
import PlanList from './PlanList'
import ToolCallList from './ToolCallList'

interface AgentResultCardProps {
  item: AgentItem
  onDecide: (decisions: Record<string, boolean>) => void
}

// One question: the plan, the tool calls so far, an approval card if paused, and the answer.
function AgentResultCard({ item, onDecide }: AgentResultCardProps) {
  const response = item.response

  return (
    <article className="space-y-3" aria-label={`Question: ${item.question}`}>
      <div className="flex justify-end">
        <p className="max-w-[75%] whitespace-pre-wrap rounded-2xl bg-blue-600 px-4 py-2 text-white">
          {item.question}
        </p>
      </div>

      <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4">
        {item.status === 'running' && (
          <p className="text-sm text-slate-400">The AI is thinking and choosing tools…</p>
        )}

        {response && response.plan.length > 0 && <PlanList steps={response.plan} />}

        {response && <ToolCallList calls={response.tool_calls} />}

        {response && (item.status === 'needs_approval' || item.status === 'deciding') && (
          <ApprovalCard
            pending={response.pending}
            disabled={item.status === 'deciding'}
            onDecide={onDecide}
          />
        )}
        {item.status === 'deciding' && <p className="text-sm text-slate-400">Continuing…</p>}

        {item.status === 'done' && response && (
          <>
            <MarkdownView markdown={response.answer} emptyText="(No answer.)" />
            <p className="text-xs text-slate-400">
              {response.steps} AI call(s) · {response.tool_calls.length} tool call(s)
              {response.usage ? ` · ${response.usage.total_tokens} tokens` : ''}
            </p>
          </>
        )}

        {item.status === 'error' && (
          <p role="alert" className="text-sm text-red-700">
            {item.error}
          </p>
        )}
      </div>
    </article>
  )
}

export default AgentResultCard
