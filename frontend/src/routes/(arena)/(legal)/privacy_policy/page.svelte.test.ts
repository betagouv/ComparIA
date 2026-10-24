import { render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import Page from './+page.svelte'

const policy = {
  version: '1',
  content_hash: 'hash',
  locale: 'fr',
  content: '# Confidentialité\n\n## Données traitées',
  published_at: '2026-07-01T00:00:00Z',
  effective_at: '2026-07-01T00:00:00Z'
}

function optOuts(data: { privacyPolicy: typeof policy | null; matomoUrl: string | null }) {
  const { container } = render(Page, { data } as never)
  return {
    divs: container.querySelectorAll('#matomo-opt-out'),
    scripts: [...container.querySelectorAll('script')].map((script) => script.src)
  }
}

describe('privacy page', () => {
  it('adds the opt-out after a published policy', () => {
    const { divs, scripts } = optOuts({
      privacyPolicy: policy,
      matomoUrl: 'https://stats.example.org'
    })

    expect(divs).toHaveLength(1)
    expect(scripts).toEqual([
      'https://stats.example.org/index.php?module=CoreAdminHome&action=optOutJS&divId=matomo-opt-out&language=fr&showIntro=1'
    ])
  })

  it('shows the opt-out once in the shipped policy', () => {
    const { divs, scripts } = optOuts({
      privacyPolicy: null,
      matomoUrl: 'https://stats.example.org'
    })

    expect(divs).toHaveLength(1)
    expect(scripts).toHaveLength(1)
  })

  it('leaves the opt-out out when Matomo is not configured', () => {
    for (const privacyPolicy of [policy, null]) {
      const { divs, scripts } = optOuts({ privacyPolicy, matomoUrl: null })

      expect(divs).toHaveLength(0)
      expect(scripts).toHaveLength(0)
    }
  })
})
