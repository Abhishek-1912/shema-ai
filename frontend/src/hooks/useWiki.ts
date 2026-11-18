import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../services/http'
import { getArticle, listArticles, listVersions } from '../services/wikiApi'
import type { ArticleDetail, ArticleStatus, ArticleSummary, ArticleVersion } from '../types/wiki'

export function errorMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : 'Something went wrong. Please try again.'
}

// The article list, optionally filtered by status.
export function useWikiList(status: ArticleStatus | undefined) {
  const [articles, setArticles] = useState<ArticleSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let ignore = false // a newer filter was chosen before this answer arrived
    listArticles(status)
      .then((data) => {
        if (!ignore) {
          setArticles(data)
          setError(null)
        }
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
  }, [status])

  return { articles, isLoading, error }
}

// One article plus its version history. `reload()` fetches both again.
export function useWikiArticle(slug: string) {
  const [article, setArticle] = useState<ArticleDetail | null>(null)
  const [versions, setVersions] = useState<ArticleVersion[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadCount, setReloadCount] = useState(0)

  useEffect(() => {
    let ignore = false
    Promise.all([getArticle(slug), listVersions(slug)])
      .then(([loadedArticle, loadedVersions]) => {
        if (!ignore) {
          setArticle(loadedArticle)
          setVersions(loadedVersions)
          setError(null)
        }
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

  const reload = useCallback(() => setReloadCount((n) => n + 1), [])

  return { article, versions, isLoading, error, reload }
}
