import { beforeEach, describe, expect, it, vi } from 'vitest'
import { load } from './+page.server'

const { request } = vi.hoisted(() => ({ request: vi.fn() }))

vi.mock('$lib/fastapi-client', () => ({ api: { request } }))
vi.mock('$lib/i18n/runtime', () => ({ getLocale: () => 'fr' }))

const document = {
  version: '1',
  content_hash: 'hash',
  locale: 'fr',
  content: '# Conditions\n\n## Objet',
  published_at: '2026-07-01T00:00:00',
  effective_at: '2026-07-01T00:00:00'
}

describe('terms page load', () => {
  beforeEach(() => {
    request.mockReset()
  })

  it('asks the backend for the active document in the current locale', async () => {
    request.mockResolvedValue(document)

    expect(await load({ fetch } as never)).toEqual({ terms: document })
    expect(request).toHaveBeenCalledWith('/settings/legal/terms?locale=fr', { fetch })
  })

  it('renders without a document when the backend is unavailable', async () => {
    request.mockRejectedValue(new Error('backend down'))

    expect(await load({ fetch } as never)).toEqual({ terms: null })
  })
})
