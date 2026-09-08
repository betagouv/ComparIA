import { render } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Commons } from '$lib/models'
import Page from './+page.svelte'

const auth = vi.hoisted(() => ({ user: null as { email: string } | null, config: {} }))
const mocks = vi.hoisted(() => ({
  goto: vi.fn(),
  invalidateAll: vi.fn(),
  openSignInModal: vi.fn()
}))

vi.mock('$app/navigation', () => ({ goto: mocks.goto, invalidateAll: mocks.invalidateAll }))

vi.mock('$lib/auth.svelte', () => ({
  getAuthContext: () => auth,
  openSignInModal: mocks.openSignInModal
}))

vi.mock('$lib/global.svelte', () => ({ getVotesContext: () => ({ count: 42, objective: 1000 }) }))

// The signed-out and empty states don't need real ranking rows, only the two
// context getters that would otherwise require a `data` context nobody sets
// up in this test.
vi.mock('$lib/models', async (importOriginal) => {
  const actual = await importOriginal<typeof import('$lib/models')>()
  const commons = { modelsCount: 0, currency: { code: 'EUR' }, rankClasses: {} } as Commons
  return {
    ...actual,
    getModelsWithDataContext: () => ({ lastUpdateDate: '01/01/2026', commons, models: [] }),
    getModelsContext: () => ({ models: [] }),
    getStyleCoefficients: () => ({})
  }
})

describe('ranking page, personal view without data', () => {
  beforeEach(() => {
    auth.user = null
    mocks.goto.mockClear()
    mocks.invalidateAll.mockClear()
    mocks.openSignInModal.mockClear()
  })

  it('blurs the real table behind a sign-in prompt when signed out', () => {
    const { container, getByRole } = render(Page, {
      data: { view: 'personal', personal: null } as never
    })

    const preview = container.querySelector('#ranking-table-preview')
    expect(preview).toBeTruthy()
    expect(preview?.closest('[inert]')).toBeTruthy()

    getByRole('button', { name: 'Se connecter' }).click()
    expect(mocks.openSignInModal).toHaveBeenCalled()
  })

  it('offers to start a comparison instead of an empty table when signed in with no votes', () => {
    auth.user = { email: 'personne@example.org' }
    const { container, getByRole, queryByRole } = render(Page, {
      data: { view: 'personal', personal: { rows: [], votes_count: 0 } } as never
    })

    expect(container.querySelector('#personal-ranking-table')).toBeNull()
    expect(container.querySelector('#ranking-table-preview')).toBeNull()
    expect(queryByRole('button', { name: 'Se connecter' })).toBeNull()
    expect(getByRole('link', { name: 'Nouvelle discussion' }).getAttribute('href')).toBe('/')
  })
})
