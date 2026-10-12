import { render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import Page from './+page.svelte'

const mocks = vi.hoisted(() => ({
  goto: vi.fn(),
  pageState: { params: { id: 'arene' }, url: new URL('http://localhost/arene') },
  authContext: { user: null, config: { access_policy: 'open', methods: [] } }
}))

vi.mock('$app/navigation', () => ({ goto: mocks.goto }))
vi.mock('$app/paths', () => ({ resolve: (path: string) => path }))
vi.mock('$app/state', () => ({ page: mocks.pageState }))
vi.mock('$lib/auth.svelte', () => ({ getAuthContext: () => mocks.authContext }))
vi.mock('$lib/authContext.svelte', async (importOriginal) => ({
  ...(await importOriginal<typeof import('$lib/authContext.svelte')>()),
  tryGetAuthContext: () => mocks.authContext
}))
vi.mock('$lib/fastapi-client', () => ({
  api: { request: () => new Promise(() => {}), getUrl: (path: string) => path }
}))
vi.mock('$lib/chatService.svelte', () => ({
  getComparison: (comparisonId: string) => ({ comparisonId, comparison: undefined }),
  getModeInfos: () => []
}))

describe('comparison page', () => {
  it('sends an id with no matching comparison back to the arena', () => {
    render(Page)

    expect(mocks.goto).toHaveBeenCalledWith('/', { replaceState: true })
  })
})
