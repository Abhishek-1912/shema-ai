import { useState } from 'react'
import { Link } from 'react-router'
import StatusBadge from '../../components/wiki/StatusBadge'
import { useWikiList } from '../../hooks/useWiki'
import type { ArticleStatus } from '../../types/wiki'

const FILTERS: { label: string; status: ArticleStatus | undefined }[] = [
  { label: 'All', status: undefined },
  { label: 'Published', status: 'published' },
  { label: 'Drafts', status: 'draft' },
  { label: 'Archived', status: 'archived' },
]

function WikiListPage() {
  const [status, setStatus] = useState<ArticleStatus | undefined>(undefined)
  const { articles, isLoading, error } = useWikiList(status)

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="mx-auto max-w-3xl">
        <header className="mb-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold">Wiki</h1>
            <p className="text-sm text-slate-500">Curated knowledge, written by your team and the AI.</p>
          </div>
          <Link to="/wiki/new" className="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700">
            + New article
          </Link>
        </header>

        <div role="tablist" aria-label="Filter by status" className="mb-4 flex gap-1">
          {FILTERS.map((filter) => (
            <button
              key={filter.label}
              type="button"
              role="tab"
              aria-selected={status === filter.status}
              onClick={() => setStatus(filter.status)}
              className={`rounded-lg px-3 py-1 text-sm ${
                status === filter.status ? 'bg-slate-800 text-white' : 'bg-white text-slate-700 hover:bg-slate-100'
              }`}
            >
              {filter.label}
            </button>
          ))}
        </div>

        {error && <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        {isLoading && <p className="text-slate-400">Loading…</p>}
        {!isLoading && !error && articles.length === 0 && (
          <p className="mt-10 text-center text-slate-400">No articles here yet.</p>
        )}

        <ul aria-label="Articles" className="space-y-2">
          {articles.map((article) => (
            <li key={article.slug}>
              <Link
                to={`/wiki/${article.slug}`}
                className="block rounded-xl border border-slate-200 bg-white p-4 hover:border-blue-400"
              >
                <div className="flex items-center gap-2">
                  <span className="font-medium">{article.title}</span>
                  <StatusBadge status={article.status} />
                  {article.created_by === 'ai' && (
                    <span className="rounded bg-purple-100 px-1.5 text-xs text-purple-700">AI</span>
                  )}
                </div>
                {article.summary && <p className="mt-1 text-sm text-slate-600">{article.summary}</p>}
                <p className="mt-1 text-xs text-slate-400">
                  v{article.version} · updated {new Date(article.updated_at).toLocaleString()}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export default WikiListPage
