import { render } from '@testing-library/svelte'
import { flushSync } from 'svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Page from './+page.svelte'

const mocks = vi.hoisted(() => ({
  goto: vi.fn(),
  pageState: { params: { id: 'arene' }, url: new URL('http://localhost/arene') },
  authContext: { user: null, config: { access_policy: 'open', methods: [] } }
}))

const store = $state<{ comparisons: { id: string; mode: string; turns: never[] }[] }>({
  comparisons: []
})

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
  getComparison: (comparisonId: string) => ({
    comparisonId,
    status: 'pending',
    get comparison() {
      return store.comparisons.find((c) => c.id === comparisonId)
    }
  }),
  getModeInfos: () => [{ value: 'random', icon: 'i-ri-dice-line', title: 'Aléatoire' }]
}))

function visit(path: string) {
  const url = new URL(`http://localhost${path}`)
  mocks.pageState.url = url
  mocks.pageState.params = { id: url.pathname.slice(1) }
}

describe('comparison page', () => {
  beforeEach(() => {
    mocks.goto.mockReset()
    store.comparisons = [{ id: 'known-id', mode: 'random', turns: [] }]
  })

  it('sends an id with no matching comparison back to the arena', () => {
    visit('/arene')
    const { container } = render(Page)

    expect(mocks.goto).toHaveBeenCalledWith('/', { replaceState: true })
    expect(container.querySelector('#send-area')).toBeNull()
  })

  it('keeps the query string so model preselection survives the redirect', () => {
    visit('/arene?c=pix&vs=model-a,model-b')
    render(Page)

    expect(mocks.goto).toHaveBeenCalledWith('/?c=pix&vs=model-a,model-b', { replaceState: true })
  })

  it('shows the chat of a known comparison', () => {
    visit('/known-id')
    const { container } = render(Page)

    expect(mocks.goto).not.toHaveBeenCalled()
    expect(container.querySelector('#send-area')).not.toBeNull()
  })

  it('leaves once the open comparison is gone, as after signing out', () => {
    visit('/known-id')
    const { container } = render(Page)

    store.comparisons = []
    flushSync()

    expect(mocks.goto).toHaveBeenCalledWith('/', { replaceState: true })
    expect(container.querySelector('#send-area')).toBeNull()
  })
})
