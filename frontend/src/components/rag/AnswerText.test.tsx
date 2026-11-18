import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { makeSource } from '../../test/fixtures'
import AnswerText from './AnswerText'
import { splitAnswer } from './citations'

describe('splitAnswer', () => {
  it('turns [n] markers into citations', () => {
    expect(splitAnswer('Return within 30 days [1][2].', new Set([1, 2]))).toEqual([
      { kind: 'text', text: 'Return within 30 days ' },
      { kind: 'citation', number: 1 },
      { kind: 'citation', number: 2 },
      { kind: 'text', text: '.' },
    ])
  })

  it('keeps numbers that are not real sources as plain text', () => {
    expect(splitAnswer('See [7] and [1].', new Set([1]))).toEqual([
      { kind: 'text', text: 'See [7] and ' },
      { kind: 'citation', number: 1 },
      { kind: 'text', text: '.' },
    ])
  })

  it('returns the text unchanged when there are no citations', () => {
    expect(splitAnswer('No sources here.', new Set([1]))).toEqual([{ kind: 'text', text: 'No sources here.' }])
  })
})

describe('AnswerText', () => {
  it('renders citations as buttons that report their number', async () => {
    const onCite = vi.fn()
    const user = userEvent.setup()
    render(
      <AnswerText
        answer="Refunds take 5 days [2]."
        sources={[makeSource(1), makeSource(2)]}
        activeNumber={null}
        onCite={onCite}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Show source 2' }))

    expect(onCite).toHaveBeenCalledWith(2)
    expect(screen.queryByRole('button', { name: 'Show source 1' })).not.toBeInTheDocument()
  })
})
