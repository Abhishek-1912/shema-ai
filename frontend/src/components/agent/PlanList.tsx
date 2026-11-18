interface PlanListProps {
  steps: string[]
}

// Module 07: the steps the agent planned BEFORE using any tools.
function PlanList({ steps }: PlanListProps) {
  return (
    <section aria-label="Plan" className="rounded-lg bg-slate-50 px-3 py-2">
      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Plan</h3>
      <ol className="list-decimal space-y-0.5 pl-5 text-sm text-slate-700">
        {steps.map((step, index) => (
          <li key={index}>{step}</li>
        ))}
      </ol>
    </section>
  )
}

export default PlanList
