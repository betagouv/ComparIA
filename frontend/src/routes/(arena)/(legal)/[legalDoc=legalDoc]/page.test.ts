import type { LegalDocumentKeys } from '$lib/generated/constants'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { load } from './+page'

const { request, env } = vi.hoisted(() => ({
  request: vi.fn(),
  env: { MATOMO_URL: 'https://stats.example.org' } as Record<string, string>
}))

vi.mock('$env/dynamic/private', () => ({ env }))
vi.mock('$lib/fastapi-client', () => ({ api: { request } }))
vi.mock('$lib/i18n/runtime', () => ({ getLocale: () => 'fr' }))

const documents = {
  terms: {
    version: '1',
    content_hash: 'hash',
    locale: 'fr',
    content: '# Conditions\n\n## Objet',
    published_at: '2026-07-01T00:00:00Z',
    effective_at: '2026-07-01T00:00:00Z'
  },
  privacy_policy: {
    version: '1',
    content_hash: 'hash',
    locale: 'fr',
    content: '# Confidentialité\n\n## Données traitées',
    published_at: '2026-07-01T00:00:00Z',
    effective_at: '2026-07-01T00:00:00Z'
  }
}

const event = (legalDoc: LegalDocumentKeys) =>
  ({
    params: { legalDoc },
    fetch
  }) as unknown as Parameters<typeof load>[0]

describe('privacy policy page load', () => {
  beforeEach(() => {
    request.mockReset()
    env.MATOMO_URL = 'https://stats.example.org'
  })

  it('asks the backend for the active document in the current locale', async () => {
    request.mockResolvedValue(documents.privacy_policy)

    expect(await load(event('privacy_policy'))).toEqual({
      doc: documents.privacy_policy,
      matomoUrl: 'https://stats.example.org'
    })
    expect(request).toHaveBeenCalledWith('/settings/legal/privacy_policy', {
      fetch,
      searchParams: { locale: 'fr' }
    })
  })

  it('falls back to the shipped policy when nothing is published', async () => {
    request.mockRejectedValue(new Error('not found'))

    expect(await load(event('privacy_policy'))).toEqual({
      doc: null,
      matomoUrl: 'https://stats.example.org'
    })
  })

  it('offers no opt-out when Matomo is not configured', async () => {
    env.MATOMO_URL = ''
    request.mockResolvedValue(documents.privacy_policy)

    expect(await load(event('privacy_policy'))).toMatchObject({ matomoUrl: null })
  })
})

describe('terms page load', () => {
  beforeEach(() => {
    request.mockReset()
  })

  it('asks the backend for the active document in the current locale', async () => {
    request.mockResolvedValue(documents.terms)

    expect(await load(event('terms'))).toEqual({ doc: documents.terms, matomoUrl: null })
    expect(request).toHaveBeenCalledWith('/settings/legal/terms', {
      fetch,
      searchParams: { locale: 'fr' }
    })
  })

  it('renders without a document when the backend is unavailable', async () => {
    request.mockRejectedValue(new Error('backend down'))

    expect(await load(event('terms'))).toEqual({ doc: null, matomoUrl: null })
  })
})
