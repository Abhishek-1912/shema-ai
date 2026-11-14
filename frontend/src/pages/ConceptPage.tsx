export interface Concept {
  title: string
  module: string
  summary: string
  points: string[]
}

// A "coming soon" page that already teaches the idea behind the tab.
function ConceptPage({ title, module, summary, points }: Concept) {
  return (
    <div className="flex-1 overflow-y-auto p-10">
      <div className="max-w-2xl">
        <p className="mb-2 inline-block rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800">
          Coming in {module}
        </p>
        <h1 className="mb-3 text-3xl font-semibold">{title}</h1>
        <p className="mb-6 text-lg text-slate-600">{summary}</p>
        <ul className="space-y-3">
          {points.map((point) => (
            <li key={point} className="rounded-xl border border-slate-200 bg-white p-4">
              {point}
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export default ConceptPage
