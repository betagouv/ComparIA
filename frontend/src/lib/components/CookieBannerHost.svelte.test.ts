import CookieBannerHost from '$lib/components/CookieBannerHost.svelte'
import { render } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { cookieConsent, page } = vi.hoisted(() => ({
  cookieConsent: {
    bannerOpen: true,
    choice: null,
    save: () => {},
    close: () => {}
  },
  page: { data: {} as Record<string, unknown> }
}))

vi.mock('$lib/stores/cookieConsent.svelte', () => ({
  getCookieConsentContext: () => cookieConsent
}))
vi.mock('$app/state', () => ({ page }))

const text = {
  title: 'Cookies on this site',
  description: 'We ask before setting cookies we do not need.',
  audience_measurement_label: 'Audience measurement',
  audience_measurement_description: 'Counts visits anonymously.',
  remembered_settings_label: 'Remembered settings',
  remembered_settings_description: 'Keeps your language and theme.'
}

describe('CookieBannerHost', () => {
  beforeEach(() => {
    cookieConsent.bannerOpen = true
    page.data = { cookieBanner: { locale: 'en', ...text } }
  })

  it('shows the banner as a region named by its title when the visitor is asked', () => {
    const { getByRole } = render(CookieBannerHost)

    expect(getByRole('region', { name: text.title })).toBeInTheDocument()
  })

  it('shows nothing once the visitor has answered', () => {
    cookieConsent.bannerOpen = false
    const { queryByRole } = render(CookieBannerHost)

    expect(queryByRole('region')).toBeNull()
  })

  it('shows nothing without the banner text', () => {
    page.data = { cookieBanner: null }
    const { queryByRole } = render(CookieBannerHost)

    expect(queryByRole('region')).toBeNull()
  })
})
