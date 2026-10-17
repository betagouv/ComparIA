import { beforeEach, describe, expect, it, vi } from 'vitest'
import { load } from './+page.server'

const { request, env } = vi.hoisted(() => ({
  request: vi.fn(),
  env: { MATOMO_URL: 'https://stats.example.org' } as Record<string, string>
}))

vi.mock('$env/dynamic/private', () => ({ env }))
vi.mock('$lib/fastapi-client', () => ({ api: { request } }))
vi.mock('$lib/i18n/runtime', () => ({ getLocale: () => 'fr' }))

const document = {
  version: '1',
  content_hash: 'hash',
  locale: 'fr',
  content: '# Confidentialité\n\n## Données traitées',
  published_at: '2026-07-01T00:00:00Z',
  effective_at: '2026-07-01T00:00:00Z'
}

describe('privacy policy page load', () => {
  beforeEach(() => {
    request.mockReset()
    env.MATOMO_URL = 'https://stats.example.org'
  })

  it('asks the backend for the active document in the current locale', async () => {
    request.mockResolvedValue(document)

    expect(await load({ fetch } as never)).toEqual({
      privacyPolicy: document,
      matomoUrl: 'https://stats.example.org'
    })
    expect(request).toHaveBeenCalledWith('/settings/legal/privacy-policy', {
      fetch,
      searchParams: { locale: 'fr' }
    })
  })

  it('falls back to the shipped policy when nothing is published', async () => {
    request.mockRejectedValue(new Error('not found'))

    expect(await load({ fetch } as never)).toEqual({
      privacyPolicy: null,
      matomoUrl: 'https://stats.example.org'
    })
  })

  it('offers no opt-out when Matomo is not configured', async () => {
    env.MATOMO_URL = ''
    request.mockResolvedValue(document)

    expect(await load({ fetch } as never)).toMatchObject({ matomoUrl: null })
  })
})
