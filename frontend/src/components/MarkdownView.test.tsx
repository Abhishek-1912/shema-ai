import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import MarkdownView from './MarkdownView'

describe('MarkdownView', () => {
  it('renders headings, bold text, lists and links', () => {
    render(<MarkdownView markdown={'# Leave\n\nYou get **15 days**.\n\n- Sick leave\n- Parental leave\n\n[Portal](https://example.com)'} />)

    expect(screen.getByRole('heading', { level: 1, name: 'Leave' })).toBeInTheDocument()
    expect(screen.getByText('15 days').tagName).toBe('STRONG')
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
    expect(screen.getByRole('link', { name: 'Portal' })).toHaveAttribute('href', 'https://example.com')
  })

  it('renders GitHub-style tables (remark-gfm)', () => {
    render(<MarkdownView markdown={'| Day | Hours |\n|---|---|\n| Saturday | 09:00-14:00 |'} />)

    expect(screen.getByRole('table')).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: '09:00-14:00' })).toBeInTheDocument()
  })

  it('never turns HTML in the text into real elements (no script injection)', () => {
    const { container } = render(
      <MarkdownView markdown={'Hello <script>window.hacked = true</script> <img src=x onerror="alert(1)">'} />,
    )

    expect(container.querySelector('script')).toBeNull()
    expect(container.querySelector('img')).toBeNull()
  })

  it('says when an article is empty', () => {
    render(<MarkdownView markdown="   " />)

    expect(screen.getByText(/This article is empty/)).toBeInTheDocument()
  })
})
