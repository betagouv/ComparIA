import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import Page from './+page.svelte'
import type { PageProps } from './$types'
import type { UsersPage } from './+page'

const goto = vi.fn()

vi.mock('$app/navigation', () => ({
  goto: (...args: unknown[]) => goto(...args),
  invalidate: vi.fn()
}))

vi.mock('$app/paths', () => ({
  resolve: (path: string) => path
}))

vi.mock('$app/state', () => ({
  page: { url: new URL('http://localhost/admin/utilisateurs') }
}))

vi.mock('$lib/auth.svelte', () => ({
  getAuthContext: () => ({ user: { email: 'me@example.org' } })
}))

vi.mock('$lib/fastapi-client', () => ({
  api: { request: vi.fn() }
}))

vi.mock('$lib/helpers/useToast.svelte', () => ({
  useToast: vi.fn()
}))

const now = new Date().toISOString()
const users: UsersPage = {
  items: [
    {
      id: '1',
      email: 'admin@example.org',
      role: 'admin',
      created_at: now,
      last_seen_at: now,
      source: 'added_manually'
    },
    {
      id: '2',
      email: 'user@example.org',
      role: 'user',
      created_at: now,
      last_seen_at: now,
      source: 'email_code'
    }
  ],
  total: 60,
  page: 1,
  page_size: 25
}

function renderPage() {
  return render(Page, {
    data: { search: '', users } as unknown as PageProps['data'],
    params: {} as PageProps['params']
  })
}

describe('admin users page', () => {
  it('shows each user role', () => {
    const { getAllByText } = renderPage()

    expect(getAllByText('admin')).toHaveLength(1)
    expect(getAllByText('user')).toHaveLength(1)
  })

  it('paginates from the server total and moves through the url', async () => {
    const { getByTitle } = renderPage()

    await fireEvent.click(getByTitle('Page suivante'))

    expect(goto).toHaveBeenCalledWith('/admin/utilisateurs?page=2')
  })
})
