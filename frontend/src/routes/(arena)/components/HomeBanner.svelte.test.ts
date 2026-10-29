import { render } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import HomeBanner from './HomeBanner.svelte'

const auth = { config: { home_banner: {} as Record<string, string> } }

vi.mock('$lib/auth.svelte', () => ({ getAuthContext: () => auth }))

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

  it('shows nothing when the current locale has no banner', () => {
    auth.config.home_banner = { en: 'Awareness tool.' }
    const { queryByRole } = render(HomeBanner)

    expect(queryByRole('note')).toBeNull()
  })
})
