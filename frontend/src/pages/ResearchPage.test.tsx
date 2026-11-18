import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../services/http'
import { runResearch } from '../services/researchApi'
import { makeResearchResponse } from '../test/fixtures'
import ResearchPage from './ResearchPage'

vi.mock('../services/researchApi', () => ({ runResearch: vi.fn() }))
const researchMock = vi.mocked(runResearch)

describe('ResearchPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('shows the report, then each researcher with its finding and tool calls', async () => {
    researchMock.mockResolvedValue(makeResearchResponse())
    const user = userEvent.setup()
    render(<ResearchPage />)

    await user.type(screen.getByRole('textbox'), 'KESTREL and the gym?{Enter}')

    const report = await screen.findByRole('region', { name: 'Report' })
    expect(report).toHaveTextContent('KESTREL is the data warehouse migration.')
    expect(researchMock).toHaveBeenCalledWith('KESTREL and the gym?')

    const team = screen.getByRole('region', { name: 'Research team' })
    expect(within(team).getByText(/2 researcher/)).toBeInTheDocument()
    await user.click(within(team).getByText('Researcher 2: Is there a company gym?'))
    expect(within(team).getByText('Not found in the documents.')).toBeVisible()
    expect(screen.getByText(/6 AI call\(s\) across all agents/)).toBeInTheDocument()
  })

  it('renders the report as Markdown (headings, bold)', async () => {
    researchMock.mockResolvedValue(makeResearchResponse({ report: '### Buying equipment\n\nUse **Form EXP-117**.' }))
    const user = userEvent.setup()
    render(<ResearchPage />)

    await user.type(screen.getByRole('textbox'), 'Equipment?{Enter}')

    expect(await screen.findByRole('heading', { level: 3, name: 'Buying equipment' })).toBeInTheDocument()
    expect(screen.getByText('Form EXP-117').tagName).toBe('STRONG')
  })

  it('runs an example question when clicked', async () => {
    researchMock.mockResolvedValue(makeResearchResponse())
    const user = userEvent.setup()
    render(<ResearchPage />)

    await user.click(screen.getByRole('button', { name: /overview for a new employee/ }))

    expect(researchMock).toHaveBeenCalledWith(expect.stringMatching(/^Give me an overview/))
    expect(await screen.findByRole('region', { name: 'Report' })).toBeInTheDocument()
  })

  it('shows a waiting message, and the error if research fails', async () => {
    let fail: (e: unknown) => void = () => {}
    researchMock.mockReturnValue(new Promise((_, reject) => (fail = reject)))
    const user = userEvent.setup()
    render(<ResearchPage />)

    await user.type(screen.getByRole('textbox'), 'Big question{Enter}')
    expect(screen.getByText(/sending researchers/)).toBeInTheDocument()
    await user.type(screen.getByRole('textbox'), 'Another one{Enter}')
    expect(researchMock).toHaveBeenCalledTimes(1) // no second research while one is running
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()

    fail(new ApiError('The AI is receiving too many requests.', 429))

    expect(await screen.findByRole('alert')).toHaveTextContent('too many requests')
  })
})
