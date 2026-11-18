import type { ComponentPropsWithoutRef, ElementType } from 'react'
import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'

// react-markdown passes an extra `node` prop (its syntax-tree data) to every element.
// It must not reach the HTML tag, or React warns about an unknown attribute.
function styled<T extends ElementType>(Tag: T, className: string) {
  return function StyledElement(props: ComponentPropsWithoutRef<T> & { node?: unknown }) {
    const { node, ...rest } = props
    void node // deliberately unused
    const Element = Tag as ElementType
    return <Element className={className} {...rest} />
  }
}

// How each Markdown element looks (Tailwind removes all default styling).
const components: Components = {
  h1: styled('h1', 'mb-3 mt-6 text-2xl font-semibold first:mt-0'),
  h2: styled('h2', 'mb-2 mt-5 text-xl font-semibold'),
  h3: styled('h3', 'mb-2 mt-4 text-lg font-semibold'),
  p: styled('p', 'mb-3 leading-relaxed'),
  ul: styled('ul', 'mb-3 list-disc space-y-1 pl-6'),
  ol: styled('ol', 'mb-3 list-decimal space-y-1 pl-6'),
  a: styled('a', 'text-blue-700 underline'),
  blockquote: styled('blockquote', 'mb-3 border-l-4 border-slate-300 pl-4 text-slate-600'),
  code: styled('code', 'rounded bg-slate-100 px-1 py-0.5 font-mono text-sm'),
  pre: styled('pre', 'mb-3 overflow-x-auto rounded-lg bg-slate-100 p-3 text-sm'),
  table: styled('table', 'mb-3 w-full border-collapse text-sm'),
  th: styled('th', 'border border-slate-300 bg-slate-50 px-2 py-1 text-left'),
  td: styled('td', 'border border-slate-300 px-2 py-1'),
}

interface MarkdownViewProps {
  markdown: string
  emptyText?: string // shown instead of nothing when the text is empty
}

// Renders Markdown as HTML (wiki articles, AI answers). react-markdown does NOT render raw
// HTML written inside the text (e.g. <script>), so a malicious article — or an AI answer
// that repeats text from a poisoned document — can't run code in the browser.
function MarkdownView({ markdown, emptyText = 'This article is empty.' }: MarkdownViewProps) {
  if (!markdown.trim()) return <p className="text-slate-400">{emptyText}</p>
  return (
    <div className="text-slate-800">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {markdown}
      </ReactMarkdown>
    </div>
  )
}

export default MarkdownView
