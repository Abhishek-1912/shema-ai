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
          Send a message to see what happens inside: what the browser sends, what the backend
          adds before calling the AI, which model answers, how many tokens it costs and how
          long it takes.
        </p>
      ) : (
        <ExchangeDetails exchange={lastExchange} />
      )}
    </aside>
  )
}

function ExchangeDetails({ exchange }: { exchange: LastExchange }) {
  const { request, historyCount, durationMs, response, error } = exchange
  const assistant = response?.assistant_message
  const usage = assistant?.usage

  return (
    <>
      <Section
        title="Browser → backend"
        hint="Only the new message is sent. The backend owns the conversation history."
      >
        <p className="mb-2 font-medium">1 new message sent</p>
        <p className="mb-2 whitespace-pre-wrap rounded-lg bg-slate-50 p-2 text-slate-700">
          {request.message}
        </p>
        <p className="text-slate-700">
          Conversation:{' '}
          <span className="font-mono text-xs">
            {request.conversation_id ?? 'new (the backend creates it)'}
          </span>
        </p>
      </Section>

      <Section
        title="Backend → AI"
        hint="The LLM has no memory, so the backend loads earlier messages from the database every time."
      >
        <ol className="list-inside list-decimal space-y-1 text-slate-700">
          <li>System prompt (added by the backend)</li>
          <li>
            {historyCount} earlier {historyCount === 1 ? 'message' : 'messages'} from the database
          </li>
          <li>Your new message</li>
        </ol>
      </Section>

      {error && (
        <Section
          title="Error"
          hint="The request failed, so no tokens were counted and nothing was saved."
        >
          <p className="rounded-lg bg-red-50 p-2 text-red-700">
            {error.status !== null && (
              <span className="mr-2 font-semibold">HTTP {error.status}</span>
            )}
            <span>{error.message}</span>
          </p>
        </Section>
      )}

      {response && assistant && (
        <>
          <Section title="Model" hint="The LLM that generated the answer.">
            <p className="font-mono">{assistant.model ?? 'unknown'}</p>
          </Section>

          <Section title="Saved" hint="Both messages were stored in Supabase.">
            <p className="text-slate-700">Question and answer saved to the database.</p>
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
