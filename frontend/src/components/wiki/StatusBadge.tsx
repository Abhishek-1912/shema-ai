import type { ArticleStatus } from '../../types/wiki'

const STYLES: Record<ArticleStatus, string> = {
  draft: 'bg-amber-100 text-amber-800',
  published: 'bg-green-100 text-green-800',
  archived: 'bg-slate-200 text-slate-600',
}

function StatusBadge({ status }: { status: ArticleStatus }) {
  return <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${STYLES[status]}`}>{status}</span>
}

export default StatusBadge
