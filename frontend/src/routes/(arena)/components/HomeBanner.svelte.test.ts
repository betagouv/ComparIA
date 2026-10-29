import { render } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import HomeBanner from './HomeBanner.svelte'

const auth = {
  config: {
    default_locale: 'en',
    enabled_locales: ['en', 'fr'],
    home_banner: {} as Record<string, string>
  }
}

vi.mock('$lib/authContext.svelte', () => ({ getAuthContext: () => auth }))

describe('HomeBanner', () => {
  beforeEach(() => {
    auth.config.home_banner = {}
  })

  it('shows the banner written for the current locale, bold included', () => {
    auth.config.home_banner = {
      fr: '**Outil de sensibilisation.** Ne saisissez aucune donnée patient.',
      en: 'Awareness tool.'
    }
    const { getByRole } = render(HomeBanner)

    const note = getByRole('note')
    expect(note.textContent).toContain('Ne saisissez aucune donnée patient.')
    expect(note.querySelector('strong')?.textContent).toBe('Outil de sensibilisation.')
  })

  it('falls back to the banner of the default locale', () => {
    auth.config.home_banner = { en: 'Awareness tool.' }
    const { getByRole } = render(HomeBanner)

    expect(getByRole('note').textContent).toContain('Awareness tool.')
  })

  it('shows nothing when the instance wrote no banner', () => {
    const { queryByRole } = render(HomeBanner)

    expect(queryByRole('note')).toBeNull()
  })
})
