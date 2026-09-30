import { isRedirect } from '@sveltejs/kit'
import { describe, expect, it, vi } from 'vitest'
import { load } from './+page'
import type { UsersPage } from './+page'

const request = vi.fn()

vi.mock('$lib/fastapi-client', () => ({
  api: { request: (...args: unknown[]) => request(...args) }
}))

async function runLoad(search: string) {
  const url = new URL(`http://localhost/admin/utilisateurs${search}`)
  return load({ depends: vi.fn(), url, fetch: vi.fn() } as unknown as Parameters<typeof load>[0])
}

async function redirectLocation(promise: Promise<unknown>) {
  try {
    await promise
  } catch (err) {
    if (isRedirect(err)) return err.location
    throw err
  }
  return null
}

describe('admin users load', () => {
  it('returns the page as served', async () => {
    const users: UsersPage = { items: [], total: 0, page: 1, page_size: 25 }
    request.mockResolvedValue(users)

    await expect(runLoad('')).resolves.toEqual({ search: '', users })
  })

  it('redirects to the last page when the requested one is past the end', async () => {
    const users: UsersPage = { items: [], total: 26, page: 3, page_size: 25 }
    request.mockResolvedValue(users)

    const location = await redirectLocation(runLoad('?page=3&page_size=25&search=foo'))

    expect(location).toBe('/admin/utilisateurs?page=2&page_size=25&search=foo')
  })

  it('does not redirect when there is nothing to list', async () => {
    const users: UsersPage = { items: [], total: 0, page: 2, page_size: 25 }
    request.mockResolvedValue(users)

    await expect(runLoad('?page=2')).resolves.toEqual({ search: '', users })
  })
})
