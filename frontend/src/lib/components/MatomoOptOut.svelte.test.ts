import { render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import MatomoOptOut from './MatomoOptOut.svelte'

const locale = vi.hoisted(() => ({ current: 'fr' }))
vi.mock('$lib/i18n/runtime', () => ({ getLocale: () => locale.current }))

function language(current: string) {
  locale.current = current
  const { container } = render(MatomoOptOut, { url: 'https://stats.example.org' })
  return new URL(container.querySelector('script')!.src).searchParams.get('language')
}

describe('Matomo opt-out', () => {
  it('asks Matomo for the visitor language', () => {
    expect(language('fr')).toBe('fr')
    expect(language('sv')).toBe('sv')
  })

  it('names Norwegian Bokmål the way Matomo does', () => {
    expect(language('nb-NO')).toBe('nb')
  })
})
