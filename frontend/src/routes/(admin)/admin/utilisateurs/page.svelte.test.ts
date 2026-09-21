import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Page from './+page.svelte'
import type { PageProps } from './$types'
import type { UsersPage } from './+page'

const { goto, pageState, request, toast } = vi.hoisted(() => ({
  goto: vi.fn(),
  pageState: { url: new URL('http://localhost/admin/utilisateurs') },
  request: vi.fn(),
  toast: vi.fn()
}))

vi.mock('$app/navigation', () => ({
  goto: (...args: unknown[]) => goto(...args),
  invalidate: vi.fn()
}))

vi.mock('$app/paths', () => ({
  resolve: (path: string) => path
}))

vi.mock('$app/state', () => ({
  page: pageState
}))

vi.mock('$lib/auth.svelte', () => ({
  getAuthContext: () => ({ user: { email: 'me@example.org' } })
}))

vi.mock('$lib/fastapi-client', () => ({
  api: { request }
}))

vi.mock('$lib/helpers/useToast.svelte', () => ({
  useToast: toast
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
      source: 'added_manually',
      totp_enabled: true
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

function renderPage(search = '') {
  return render(Page, {
    data: { search, users } as unknown as PageProps['data'],
    params: {} as PageProps['params']
  })
}

describe('admin users page', () => {
  beforeEach(() => {
    goto.mockClear()
    request.mockReset()
    toast.mockClear()
    pageState.url = new URL('http://localhost/admin/utilisateurs')
    Object.defineProperty(window, 'dsfr', {
      configurable: true,
      value: () => ({ modal: { disclose: vi.fn(), conceal: vi.fn() } })
    })
  })

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

  it('navigates once per page change', async () => {
    const { getByTitle } = renderPage()

    await fireEvent.click(getByTitle('Page suivante'))

    expect(goto).toHaveBeenCalledTimes(1)
  })

  it('says so when there is no 2FA left to reset', async () => {
    request.mockRejectedValue(
      Object.assign(new Error('Error 404 [DELETE](/admin/users/1/totp): Not Found'), {
        status: 404
      })
    )
    const { getByTitle, container } = renderPage()

    await fireEvent.click(getByTitle('Reset 2FA'))
    // The dialog is closed as far as jsdom knows, so roles do not reach into it.
    const modal = container.querySelector('#fr-modal-reset-totp')!
    await fireEvent.click(
      [...modal.querySelectorAll('button')].find(
        (b) => b.textContent?.trim() === 'Reset 2FA for admin@example.org'
      )!
    )

    await waitFor(() =>
      expect(toast).toHaveBeenCalledWith('admin@example.org has no 2FA to reset', 6000, 'error')
    )
    expect(request).toHaveBeenCalledWith('/admin/users/1/totp', { method: 'DELETE' })
  })

  it('builds the next url from the current one, not the one at mount', async () => {
    pageState.url = new URL('http://localhost/admin/utilisateurs?search=foo')
    const { getByTitle, rerender } = renderPage('foo')

    // A browser Back that drops the search from the url.
    pageState.url = new URL('http://localhost/admin/utilisateurs')
    await rerender({ data: { search: '', users } as unknown as PageProps['data'] })
    await fireEvent.click(getByTitle('Page suivante'))

    expect(goto).toHaveBeenCalledWith('/admin/utilisateurs?page=2')
  })
})
