import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import MarkdownView from '../../components/MarkdownView'
import StatusBadge from '../../components/wiki/StatusBadge'
import VersionHistory from '../../components/wiki/VersionHistory'
import { errorMessage, useWikiArticle } from '../../hooks/useWiki'
import { deleteArticle, restoreVersion, setArticleStatus } from '../../services/wikiApi'

function WikiArticlePage() {
  const { slug = '' } = useParams()
  const navigate = useNavigate()
  const { article, versions, isLoading, error, reload } = useWikiArticle(slug)
  const [actionError, setActionError] = useState<string | null>(null)
  const [isWorking, setIsWorking] = useState(false)
  const [showHistory, setShowHistory] = useState(false)

  // Run a change, then reload the article and its history.
  async function act(action: () => Promise<unknown>) {
    setActionError(null)
    setIsWorking(true)
    try {
      await action()
      reload()
    } catch (err) {
      setActionError(errorMessage(err))
    } finally {
      setIsWorking(false)
    }
  }

  async function handleDelete() {
    if (!article || !window.confirm(`Delete "${article.title}" and its whole history? This cannot be undone.`)) return
    try {
      await deleteArticle(slug)
      navigate('/wiki', { replace: true })
    } catch (err) {
      setActionError(errorMessage(err))
    }
  }

  if (isLoading) return <p className="p-6 text-slate-400">Loading…</p>
  if (error || !article) {
    return (
      <div className="p-6">
        <p role="alert" className="mb-3 text-red-700">{error ?? 'Article not found.'}</p>
        <Link to="/wiki" className="text-blue-700 underline">Back to the wiki</Link>
      </div>
    )
  }

  return (
    <div className="flex min-w-0 flex-1">
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-3xl">
          <Link to="/wiki" className="text-sm text-blue-700 hover:underline">← All articles</Link>

          <header className="mb-4 mt-2">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-3xl font-semibold">{article.title}</h1>
              <StatusBadge status={article.status} />
            </div>
            {article.summary && <p className="mt-1 text-slate-600">{article.summary}</p>}
            <p className="mt-1 text-xs text-slate-400">
              Version {article.version} · updated {new Date(article.updated_at).toLocaleString()}
              {article.created_by === 'ai' ? ' · drafted by AI' : ''}
            </p>
          </header>

          <div className="mb-6 flex flex-wrap gap-2">
            <Link to={`/wiki/${slug}/edit`} className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700">
              Edit
            </Link>
            {article.status !== 'published' && (
              <button type="button" disabled={isWorking} onClick={() => void act(() => setArticleStatus(slug, 'publish'))}
                className="rounded-lg border border-green-600 px-3 py-1.5 text-sm text-green-700 hover:bg-green-50 disabled:opacity-50">
                Publish
              </button>
            )}
            {article.status === 'published' && (
              <button type="button" disabled={isWorking} onClick={() => void act(() => setArticleStatus(slug, 'archive'))}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50 disabled:opacity-50">
                Archive
              </button>
            )}
            <button type="button" aria-pressed={showHistory} onClick={() => setShowHistory((v) => !v)}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50">
              {showHistory ? 'Hide history' : `History (${versions.length})`}
            </button>
            <button type="button" onClick={() => void handleDelete()}
              className="rounded-lg border border-red-300 px-3 py-1.5 text-sm text-red-700 hover:bg-red-50">
              Delete
            </button>
          </div>

          {actionError && <p role="alert" className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{actionError}</p>}

          <article>
            <MarkdownView markdown={article.content} />
          </article>
        </div>
      </div>

      {showHistory && (
        <VersionHistory
          versions={versions}
          currentVersion={article.version}
          disabled={isWorking}
          onRestore={(version) => void act(() => restoreVersion(slug, version, article.version))}
        />
      )}
    </div>
  )
}

export default WikiArticlePage
