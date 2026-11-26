import { fireEvent, render } from '@testing-library/svelte'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { PageData, PageProps } from './$types'
import Page from './+page.svelte'

const cookieConsent = vi.hoisted(() => ({ enabled: false, reopen: vi.fn() }))
vi.mock('$lib/stores/cookieConsent.svelte', () => ({
  getCookieConsentContext: () => cookieConsent
}))

const stats = { url: 'https://stats.example.org', id: '1' }

const policy = {
  version: '1',
  content_hash: 'hash',
  locale: 'fr',
  content: '# Confidentialité\n\n## Données traitées',
  published_at: '2026-07-01T00:00:00Z',
  effective_at: '2026-07-01T00:00:00Z'
}

function renderPolicy(data: {
  privacyPolicy: typeof policy | null
  measurement: { url: string; id: string } | null
}) {
  return render(Page, {
    data: data as unknown as PageData,
    params: { legalDoc: 'privacy_policy' }
  } as PageProps)
}

function optOuts(data: {
  privacyPolicy: typeof policy | null
  measurement: { url: string; id: string } | null
}) {
  const { container } = renderPolicy(data)
  return {
    divs: container.querySelectorAll('#matomo-opt-out'),
    scripts: [...container.querySelectorAll('script')].map((script) => script.src)
  }
}

describe('privacy page', () => {
  it('adds the opt-out after a published policy', () => {
    const { divs, scripts } = optOuts({
      privacyPolicy: policy,
      measurement: stats
    })

    expect(divs).toHaveLength(1)
    expect(scripts).toEqual([
      'https://stats.example.org/index.php?module=CoreAdminHome&action=optOutJS&divId=matomo-opt-out&language=fr&showIntro=1'
    ])
  })

  it('shows the opt-out once in the shipped policy', () => {
    const { divs, scripts } = optOuts({
      privacyPolicy: null,
      measurement: stats
    })

    expect(divs).toHaveLength(1)
    expect(scripts).toHaveLength(1)
  })

  it('leaves the opt-out out when nothing is measured', () => {
    for (const privacyPolicy of [policy, null]) {
      const { divs, scripts } = optOuts({ privacyPolicy, measurement: null })

      expect(divs).toHaveLength(0)
      expect(scripts).toHaveLength(0)
    }
  })
})

describe('privacy page with the cookie banner on', () => {
  afterEach(() => {
    cookieConsent.enabled = false
    cookieConsent.reopen.mockClear()
  })

  it('reopens the banner instead of loading the Matomo opt-out', async () => {
    cookieConsent.enabled = true
    const { container, getByRole } = renderPolicy({
      privacyPolicy: policy,
      measurement: stats
    })

    expect(container.querySelectorAll('#matomo-opt-out')).toHaveLength(0)
    expect(container.querySelectorAll('script')).toHaveLength(0)

    await fireEvent.click(getByRole('button', { name: 'Gérer les cookies' }))
    expect(cookieConsent.reopen).toHaveBeenCalledOnce()
  })
})
