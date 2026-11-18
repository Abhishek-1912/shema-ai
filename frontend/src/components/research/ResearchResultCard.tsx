import type { ResearchItem } from '../../types/research'
import MarkdownView from '../MarkdownView'
import ToolCallList from '../agent/ToolCallList'

// One research question: the finished report first, then how the team got there.
function ResearchResultCard({ item }: { item: ResearchItem }) {
  const response = item.response

  return (
    <article className="space-y-3" aria-label={`Research: ${item.question}`}>
      <div className="flex justify-end">
        <p className="max-w-[75%] whitespace-pre-wrap rounded-2xl bg-blue-600 px-4 py-2 text-white">
          {item.question}
        </p>
      </div>

      <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4">
        {item.status === 'running' && (
          <p className="text-sm text-slate-400">
            Splitting the question and sending researchers… this can take up to a minute.
          </p>
        )}

        {item.status === 'error' && (
          <p role="alert" className="text-sm text-red-700">
            {item.error}
          </p>
        )}

        {response && (
          <>
            <section aria-label="Report">
              <MarkdownView markdown={response.report} emptyText="(No report.)" />
            </section>

            <section aria-label="Research team" className="space-y-2">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                How it was researched: {response.findings.length} researcher(s)
              </h3>
              {response.findings.map((finding, index) => (
                <details key={index} className="rounded-lg bg-slate-50 px-3 py-2 text-sm">
                  <summary className="cursor-pointer font-medium">
                    Researcher {index + 1}: {finding.sub_question}
                  </summary>
                  <div className="mt-2 text-slate-700">
                    <MarkdownView markdown={finding.answer} emptyText="Not found in the documents." />
                  </div>
                  <div className="mt-2">
                    <ToolCallList calls={finding.tool_calls} />
                  </div>
                </details>
              ))}
            </section>

            <p className="text-xs text-slate-400">
              {response.steps} AI call(s) across all agents
              {response.usage ? ` · ${response.usage.total_tokens} tokens` : ''}
            </p>
          </>
        )}
      </div>
    </article>
  )
}

export default ResearchResultCard
