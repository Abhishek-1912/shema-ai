import type { ArticleDetail, ArticleInput, ArticleStatus, ArticleSummary, ArticleVersion } from '../types/wiki'
import { isObject, readJson, send } from './http'

// ---------------------------------------------------------------------------
// Wiki endpoints (docs/api-contract.md, version 5)
// ---------------------------------------------------------------------------

const JSON_HEADERS = { 'Content-Type': 'application/json' }

function articleUrl(slug: string, suffix = ''): string {
  return `/api/wiki/${encodeURIComponent(slug)}${suffix}`
}

export async function listArticles(status?: ArticleStatus): Promise<ArticleSummary[]> {
  const url = status ? `/api/wiki?status=${status}` : '/api/wiki'
  const data = await readJson(await send(url), isArticleList)
  return data.articles
}

export async function getArticle(slug: string): Promise<ArticleDetail> {
  return readJson(await send(articleUrl(slug)), isArticleDetail)
}

export async function createArticle(input: ArticleInput): Promise<ArticleDetail> {
  const response = await send('/api/wiki', { method: 'POST', headers: JSON_HEADERS, body: JSON.stringify(input) })
  return readJson(response, isArticleDetail)
}

// expectedVersion = the version the user started editing (optimistic locking → 409 on conflict)
export async function updateArticle(
  slug: string,
  input: ArticleInput & { change_note?: string },
  expectedVersion: number,
): Promise<ArticleDetail> {
  const response = await send(articleUrl(slug), {
    method: 'PUT',
    headers: JSON_HEADERS,
    body: JSON.stringify({ ...input, expected_version: expectedVersion }),
  })
  return readJson(response, isArticleDetail)
}

export async function deleteArticle(slug: string): Promise<void> {
  await send(articleUrl(slug), { method: 'DELETE' })
}

export async function listVersions(slug: string): Promise<ArticleVersion[]> {
  const data = await readJson(await send(articleUrl(slug, '/versions')), isVersionList)
  return data.versions
}

export async function restoreVersion(slug: string, version: number, expectedVersion: number): Promise<ArticleDetail> {
  const response = await send(articleUrl(slug, '/restore'), {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({ version, expected_version: expectedVersion }),
  })
  return readJson(response, isArticleDetail)
}

export async function setArticleStatus(slug: string, action: 'publish' | 'archive'): Promise<ArticleDetail> {
  return readJson(await send(articleUrl(slug, `/${action}`), { method: 'POST' }), isArticleDetail)
}

// --- Shape checks ------------------------------------------------------------------

function isArticleSummary(data: unknown): data is ArticleSummary {
  return isObject(data) && typeof data.slug === 'string' && typeof data.title === 'string' && typeof data.version === 'number'
}

function isArticleDetail(data: unknown): data is ArticleDetail {
  return isArticleSummary(data) && isObject(data) && typeof data.content === 'string'
}

function isArticleList(data: unknown): data is { articles: ArticleSummary[] } {
  return isObject(data) && Array.isArray(data.articles) && data.articles.every(isArticleSummary)
}

function isVersionList(data: unknown): data is { versions: ArticleVersion[] } {
  return (
    isObject(data) &&
    Array.isArray(data.versions) &&
    data.versions.every((v) => isObject(v) && typeof v.version === 'number' && typeof v.content === 'string')
  )
}
