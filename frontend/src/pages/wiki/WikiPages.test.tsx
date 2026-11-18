import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../services/http'
import {
  createArticle,
  getArticle,
  listArticles,
  listVersions,
  restoreVersion,
  setArticleStatus,
  updateArticle,
} from '../../services/wikiApi'
import { makeArticle, makeVersion } from '../../test/fixtures'
import WikiArticlePage from './WikiArticlePage'
import WikiEditorPage from './WikiEditorPage'
import WikiListPage from './WikiListPage'

vi.mock('../../services/wikiApi', () => ({
  listArticles: vi.fn(),
  getArticle: vi.fn(),
  createArticle: vi.fn(),
  updateArticle: vi.fn(),
  deleteArticle: vi.fn(),
  listVersions: vi.fn(),
  restoreVersion: vi.fn(),
  setArticleStatus: vi.fn(),
}))

function CurrentPath() {
  return <p data-testid="path">{useLocation().pathname}</p>
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/wiki" element={<WikiListPage />} />
        <Route path="/wiki/new" element={<WikiEditorPage />} />
        <Route path="/wiki/:slug" element={<WikiArticlePage />} />
        <Route path="/wiki/:slug/edit" element={<WikiEditorPage />} />
      </Routes>
      <CurrentPath />
    </MemoryRouter>,
  )
}

describe('Wiki pages', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(listArticles).mockResolvedValue([makeArticle()])
    vi.mocked(getArticle).mockResolvedValue(makeArticle())
    vi.mocked(listVersions).mockResolvedValue([makeVersion(2, 'new text'), makeVersion(1, 'old text')])
  })

  // --- List --------------------------------------------------------------------------

  it('lists articles and filters by status', async () => {
    const user = userEvent.setup()
    renderAt('/wiki')

    const list = await screen.findByRole('list', { name: 'Articles' })
    expect(within(list).getByText('Remote work')).toBeInTheDocument()
    expect(within(list).getByText('Home office rules')).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'Published' }))
    await waitFor(() => expect(listArticles).toHaveBeenLastCalledWith('published'))
  })

  // --- Article view --------------------------------------------------------------------

  it('shows the article rendered from Markdown', async () => {
    renderAt('/wiki/remote-work')

    expect(await screen.findByRole('heading', { level: 1, name: 'Remote work' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Rules' })).toBeInTheDocument()
    expect(screen.getByText('3 days').tagName).toBe('STRONG')
  })

  it('publishes a draft and reloads it', async () => {
    vi.mocked(setArticleStatus).mockResolvedValue(makeArticle({ status: 'published' }))
    const user = userEvent.setup()
    renderAt('/wiki/remote-work')

    await user.click(await screen.findByRole('button', { name: 'Publish' }))

    expect(setArticleStatus).toHaveBeenCalledWith('remote-work', 'publish')
    await waitFor(() => expect(getArticle).toHaveBeenCalledTimes(2)) // reloaded after the change
  })

  it('restores an older version from the history panel', async () => {
    vi.mocked(restoreVersion).mockResolvedValue(makeArticle({ version: 3 }))
    const user = userEvent.setup()
    renderAt('/wiki/remote-work')

    await user.click(await screen.findByRole('button', { name: 'History (2)' }))
    const history = screen.getByRole('complementary', { name: 'Version history' })
    await user.click(within(history).getByRole('button', { name: /Version 1/ }))
    await user.click(within(history).getByRole('button', { name: 'Restore version 1' }))

    expect(restoreVersion).toHaveBeenCalledWith('remote-work', 1, 2)
  })

  // --- Editor --------------------------------------------------------------------------

  it('creates a new draft and opens it', async () => {
    vi.mocked(createArticle).mockResolvedValue(makeArticle({ slug: 'parking', title: 'Parking', version: 1 }))
    const user = userEvent.setup()
    renderAt('/wiki/new')

    await user.type(screen.getByLabelText('Title'), 'Parking')
    await user.type(screen.getByLabelText('Content (Markdown)'), 'Visitors book a day ahead.')
    await user.click(screen.getByRole('button', { name: 'Create draft' }))

    expect(createArticle).toHaveBeenCalledWith({ title: 'Parking', content: 'Visitors book a day ahead.', summary: undefined })
    await waitFor(() => expect(screen.getByTestId('path')).toHaveTextContent('/wiki/parking'))
  })

  it('shows a Markdown preview', async () => {
    const user = userEvent.setup()
    renderAt('/wiki/new')

    await user.type(screen.getByLabelText('Content (Markdown)'), '**bold**')
    await user.click(screen.getByRole('tab', { name: 'preview' }))

    expect(screen.getByText('bold').tagName).toBe('STRONG')
  })

  it('saves an edit with the version it started from', async () => {
    vi.mocked(updateArticle).mockResolvedValue(makeArticle({ version: 3 }))
    const user = userEvent.setup()
    renderAt('/wiki/remote-work/edit')

    const content = await screen.findByLabelText('Content (Markdown)')
    await user.clear(content)
    await user.type(content, 'Four days now.')
    await user.type(screen.getByLabelText(/What did you change/), 'Policy update')
    await user.click(screen.getByRole('button', { name: 'Save new version' }))

    expect(updateArticle).toHaveBeenCalledWith(
      'remote-work',
      { title: 'Remote work', content: 'Four days now.', summary: 'Home office rules', change_note: 'Policy update' },
      2,
    )
    await waitFor(() => expect(screen.getByTestId('path')).toHaveTextContent(/^\/wiki\/remote-work$/))
  })

  it('on a conflict keeps the user text and offers to load the latest version', async () => {
    vi.mocked(updateArticle).mockRejectedValue(
      new ApiError('Someone else changed this article after you opened it.', 409),
    )
    const user = userEvent.setup()
    renderAt('/wiki/remote-work/edit')

    const content = await screen.findByLabelText('Content (Markdown)')
    await user.clear(content)
    await user.type(content, 'My unsaved text')
    await user.click(screen.getByRole('button', { name: 'Save new version' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Someone else changed this article')
    expect(screen.getByLabelText('Content (Markdown)')).toHaveValue('My unsaved text') // not lost
    expect(screen.getByTestId('path')).toHaveTextContent('/wiki/remote-work/edit') // stayed in the editor

    vi.mocked(getArticle).mockResolvedValue(makeArticle({ version: 3, content: 'Their newer text' }))
    await user.click(screen.getByRole('button', { name: /load the latest version/ }))

    await waitFor(() => expect(screen.getByLabelText('Content (Markdown)')).toHaveValue('Their newer text'))
    expect(screen.getByRole('heading', { name: 'Edit (version 3)' })).toBeInTheDocument()
  })
})
