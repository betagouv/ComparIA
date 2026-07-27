import { beforeEach, describe, expect, it, vi } from 'vitest'
import { load } from './+page.server'

const { request } = vi.hoisted(() => ({ request: vi.fn() }))

vi.mock('$lib/fastapi-client', () => ({ api: { request } }))
vi.mock('$lib/i18n/runtime', () => ({ getLocale: () => 'fr' }))

const document = {
  version: '1',
  content_hash: 'hash',
  locale: 'fr',
  content: '# Confidentialité\n\n## Données traitées',
  published_at: '2026-07-01T00:00:00',
  effective_at: '2026-07-01T00:00:00'
}

describe('privacy policy page load', () => {
  beforeEach(() => {
    request.mockReset()
  })

  it('asks the backend for the active document in the current locale', async () => {
    request.mockResolvedValue(document)

    expect(await load({ fetch } as never)).toEqual({ privacyPolicy: document })
    expect(request).toHaveBeenCalledWith('/settings/legal/privacy-policy?locale=fr', { fetch })
  })

  it('falls back to the shipped policy when nothing is published', async () => {
    request.mockRejectedValue(new Error('not found'))

    expect(await load({ fetch } as never)).toEqual({ privacyPolicy: null })
  })
})
