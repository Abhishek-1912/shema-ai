import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import MarkdownView from '../../components/wiki/MarkdownView'
import { errorMessage } from '../../hooks/useWiki'
import { ApiError } from '../../services/http'
import { createArticle, getArticle, updateArticle } from '../../services/wikiApi'

// Used for both /wiki/new (create) and /wiki/:slug/edit (edit).
function WikiEditorPage() {
  const { slug } = useParams()
  const isNew = slug === undefined
  const navigate = useNavigate()

  const [title, setTitle] = useState('')
  const [summary, setSummary] = useState('')
  const [content, setContent] = useState('')
  const [changeNote, setChangeNote] = useState('')
  const [baseVersion, setBaseVersion] = useState<number | null>(null) // the version being edited
  const [tab, setTab] = useState<'write' | 'preview'>('write')
  const [isLoading, setIsLoading] = useState(!isNew)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [conflict, setConflict] = useState(false)
  const [reloadCount, setReloadCount] = useState(0)

  // Load the article to edit (and again after "load the latest version").
  useEffect(() => {
    if (slug === undefined) return
    let ignore = false
    getArticle(slug)
      .then((article) => {
        if (ignore) return
        setTitle(article.title)
        setSummary(article.summary ?? '')
        setContent(article.content)
        setBaseVersion(article.version)
        setConflict(false)
        setError(null)
      })
      .catch((err: unknown) => {
        if (!ignore) setError(errorMessage(err))
      })
      .finally(() => {
        if (!ignore) setIsLoading(false)
      })
    return () => {
      ignore = true
    }
  }, [slug, reloadCount])

  async function save() {
    setError(null)
    setConflict(false)
    setIsSaving(true)
    const input = { title, content, summary: summary.trim() || undefined }
    try {
      const saved = isNew
        ? await createArticle(input)
        : await updateArticle(slug, { ...input, change_note: changeNote.trim() || undefined }, baseVersion ?? 1)
      navigate(`/wiki/${saved.slug}`)
    } catch (err) {
      // 409 on an edit = someone else saved after we opened the article.
      if (!isNew && err instanceof ApiError && err.status === 409) setConflict(true)
      setError(errorMessage(err))
    } finally {
      setIsSaving(false)
    }
  }

  if (isLoading) return <p className="p-6 text-slate-400">Loading…</p>

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <form
        className="mx-auto max-w-3xl space-y-4"
        onSubmit={(event) => {
          event.preventDefault()
          void save()
        }}
      >
        <header className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">{isNew ? 'New article' : `Edit (version ${baseVersion})`}</h1>
          <Link to={isNew ? '/wiki' : `/wiki/${slug}`} className="text-sm text-blue-700 hover:underline">Cancel</Link>
        </header>

        {error && (
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            <p>{error}</p>
            {conflict && (
              <>
                <p className="mt-1 text-slate-700">
                  Your text is still below. Copy anything you want to keep, then load the latest version.
                </p>
                <button type="button" onClick={() => setReloadCount((n) => n + 1)}
                  className="mt-2 rounded-lg border border-red-300 bg-white px-3 py-1 font-medium hover:bg-red-50">
                  Discard my changes and load the latest version
                </button>
              </>
            )}
          </div>
        )}

        <label className="block">
          <span className="text-sm font-medium">Title</span>
          <input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} required
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-blue-500 focus:outline-none" />
        </label>

        <label className="block">
          <span className="text-sm font-medium">Summary (optional)</span>
          <input value={summary} onChange={(e) => setSummary(e.target.value)} maxLength={500}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-blue-500 focus:outline-none" />
        </label>

        <div>
          <div role="tablist" aria-label="Editor mode" className="mb-1 flex gap-1">
            {(['write', 'preview'] as const).map((mode) => (
              <button key={mode} type="button" role="tab" aria-selected={tab === mode} onClick={() => setTab(mode)}
                className={`rounded-t-lg px-3 py-1 text-sm capitalize ${tab === mode ? 'bg-white font-medium' : 'text-slate-500'}`}>
                {mode}
              </button>
            ))}
          </div>
          {tab === 'write' ? (
            <textarea
              aria-label="Content (Markdown)"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={18}
              maxLength={50_000}
              placeholder={'# Heading\n\nWrite in **Markdown**: lists with -, links with [text](url)...'}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none"
            />
          ) : (
            <div className="min-h-64 rounded-lg border border-slate-200 bg-white p-4">
              <MarkdownView markdown={content} />
            </div>
          )}
        </div>

        {!isNew && (
          <label className="block">
            <span className="text-sm font-medium">What did you change? (optional)</span>
            <input value={changeNote} onChange={(e) => setChangeNote(e.target.value)} maxLength={300}
              placeholder="e.g. Updated the number of home-office days"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-blue-500 focus:outline-none" />
          </label>
        )}

        <button type="submit" disabled={isSaving || !title.trim()}
          className="rounded-lg bg-blue-600 px-5 py-2 font-medium text-white hover:bg-blue-700 disabled:bg-slate-300">
          {isSaving ? 'Saving…' : isNew ? 'Create draft' : 'Save new version'}
        </button>
      </form>
    </div>
  )
}

export default WikiEditorPage
