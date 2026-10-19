import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { InformationalLegalPageLinks } from '$lib/generated/backend'
import { informationalLegalPageLink, informationalLegalPageLinks } from '$lib/testing/mock-data'
import { load } from './+page'

const { request } = vi.hoisted(() => ({
  request: vi.fn()
}))

vi.mock('$lib/fastapi-client', () => ({ api: { request } }))

const event = (
  infoPage: string,
  infoPageLinks: InformationalLegalPageLinks = informationalLegalPageLinks
) =>
  ({
    params: { infoPage },
    parent: async () => ({
      informationalPagesLinks: infoPageLinks
    })
  }) as unknown as Parameters<typeof load>[0]

describe('Informational legal pages load', () => {
  beforeEach(() => {
    request.mockReset()
  })

  it('returns content or null for a valid param', async () => {
    const page = { content: '', locale: 'fr' }
    request.mockResolvedValue({ content: '', locale: 'fr' })
    await expect(load(event('accessibility'))).resolves.toEqual({ page })

    request.mockResolvedValue(null)
    await expect(load(event('accessibility'))).resolves.toEqual({ page: null })
  })

  it('returns 404 for a invalid param', async () => {
    await expect(load(event('access'))).rejects.toMatchObject({
      status: 404
    })
  })

  it('redirects for page with external link', async () => {
    const infoPageLinks = {
      accessibility: informationalLegalPageLink({
        mode: 'external',
        external_url: 'https://example.gouv.fr/eco-design'
      })
    }
    await expect(load(event('accessibility', infoPageLinks))).rejects.toMatchObject({
      status: 307,
      location: 'https://example.gouv.fr/eco-design'
    })
  })
})
