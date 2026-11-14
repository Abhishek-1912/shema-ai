import type { ReactNode } from 'react'
import type { LastExchange } from '../types/chat'

interface UnderTheHoodPanelProps {
  lastExchange: LastExchange | null
}

// Shows what happened inside the most recent request. Pure display: no logic, no state.
function UnderTheHoodPanel({ lastExchange }: UnderTheHoodPanelProps) {
  return (
    <aside
      aria-label="Under the hood"
      className="flex w-96 shrink-0 flex-col gap-5 overflow-y-auto border-l border-slate-200 bg-white p-5 text-sm"
    >
      <h2 className="text-base font-semibold">Under the hood</h2>

      {lastExchange === null ? (
        <p className="text-slate-500">
          Send a message to see what happens inside: what is sent to the AI, which model
          answers, how many tokens it costs and how long it takes.
        </p>
      ) : (
        <ExchangeDetails exchange={lastExchange} />
      )}
    </aside>
  )
}

function ExchangeDetails({ exchange }: { exchange: LastExchange }) {
  const { sentMessages, durationMs, response, error } = exchange
  const usage = response?.usage

  return (
    <>
      <Section
        title="Messages sent"
        hint="The LLM has no memory: the whole conversation is sent every time."
      >
        <p className="mb-2 font-medium">{sentMessages.length} messages sent</p>
        <ol className="max-h-64 space-y-2 overflow-y-auto">
          {sentMessages.map((message, index) => (
            // The list is a snapshot that never re-orders, so the index is a stable key here.
            <li key={index} className="rounded-lg bg-slate-50 p-2">
              <span
                className={`mb-1 inline-block rounded px-1.5 text-xs font-medium ${
                  message.role === 'user'
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-slate-200 text-slate-700'
                }`}
              >
                {message.role}
              </span>
              <p className="whitespace-pre-wrap text-slate-700">{message.content}</p>
            </li>
          ))}
        </ol>
      </Section>

      {error && (
        <Section title="Error" hint="The request failed, so no tokens were counted.">
          <p className="rounded-lg bg-red-50 p-2 text-red-700">
            {error.status !== null && (
              <span className="mr-2 font-semibold">HTTP {error.status}</span>
            )}
            <span>{error.message}</span>
          </p>
        </Section>
      )}

      {response && (
        <>
          <Section title="Model" hint="The LLM that generated the answer.">
            <p className="font-mono">{response.model}</p>
          </Section>

          <Section
            title="Tokens"
            hint="Text is split into tokens (pieces of words). You pay per token, in and out."
          >
            {usage ? (
              <dl className="grid grid-cols-4 gap-2 text-center">
                <Stat label="Input" value={usage.input_tokens} />
                <Stat label="Output" value={usage.output_tokens} />
                <Stat label="Thinking" value={usage.thinking_tokens} />
                <Stat label="Total" value={usage.total_tokens} />
              </dl>
            ) : (
              <p className="text-slate-500">Not reported by the provider.</p>
            )}
          </Section>
        </>
      )}

      <Section title="Time" hint="Browser → backend → AI → back to the browser.">
        <p className="font-mono">{(durationMs / 1000).toFixed(2)} s</p>
      </Section>
    </>
  )
}

function Section({ title, hint, children }: { title: string; hint: string; children: ReactNode }) {
  return (
    <section>
      <h3 className="font-semibold text-slate-900">{title}</h3>
      <p className="mb-2 text-xs text-slate-500">{hint}</p>
      {children}
    </section>
  )
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg bg-slate-50 p-2">
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="font-mono text-base font-semibold">{value}</dd>
    </div>
  )
}

export default UnderTheHoodPanel
