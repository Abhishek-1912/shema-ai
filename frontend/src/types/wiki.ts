// API shapes for the wiki — must match docs/api-contract.md (version 5)

export type ArticleStatus = 'draft' | 'published' | 'archived'

export interface ArticleSummary {
  slug: string
  title: string
  summary: string | null
  status: ArticleStatus
  version: number
  created_by: 'user' | 'ai'
  updated_at: string
}

export interface ArticleDetail extends ArticleSummary {
  content: string // Markdown
  created_at: string
}

export interface ArticleVersion {
  version: number
  title: string
  content: string
  change_note: string | null
  created_by: 'user' | 'ai'
  created_at: string
}

export interface ArticleInput {
  title: string
  content: string
  summary?: string
}
