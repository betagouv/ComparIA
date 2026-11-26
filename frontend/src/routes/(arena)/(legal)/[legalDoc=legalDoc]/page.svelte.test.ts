import { measurementInUse } from '$lib/matomo'
import { fireEvent, render } from '@testing-library/svelte'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { PageData, PageProps } from './$types'
import { load as loadRootLayout } from '../../../+layout.server'
import Page from './+page.svelte'

const cookieConsent = vi.hoisted(() => ({
  asking: false,
  decision: { showBanner: false, loadMeasurement: true },
  reopen: vi.fn()
}))
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

  it('points the opt-out at the admin’s Matomo when they switched it on', async () => {
    const measurement = measurementInUse(
      {
        matomo_enabled: true,
        matomo_url: 'https://own-stats.example.org/matomo',
        matomo_site_id: '7'
      },
      { MATOMO_URL: 'https://stats.example.org', MATOMO_ID: '1' }
    )
    const layout = await loadRootLayout({
      locals: { cookieBannerEnabled: false, measurement }
    } as unknown as Parameters<typeof loadRootLayout>[0])

    const { scripts } = optOuts({ privacyPolicy: policy, measurement: layout!.measurement })

    expect(scripts).toEqual([
      'https://own-stats.example.org/matomo/index.php?module=CoreAdminHome&action=optOutJS&divId=matomo-opt-out&language=fr&showIntro=1'
    ])
  })

  it('leaves the opt-out out while the tracker is held back', () => {
    cookieConsent.decision = { showBanner: false, loadMeasurement: false }
    try {
      const { divs, scripts } = optOuts({ privacyPolicy: policy, measurement: stats })

      expect(divs).toHaveLength(0)
      expect(scripts).toHaveLength(0)
    } finally {
      cookieConsent.decision = { showBanner: false, loadMeasurement: true }
    }
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
    cookieConsent.asking = false
    cookieConsent.reopen.mockClear()
  })

  it('reopens the banner instead of loading the Matomo opt-out', async () => {
    cookieConsent.asking = true
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
