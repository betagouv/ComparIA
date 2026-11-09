import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getLocalesContext } from './global.svelte'

const config = { default_locale: 'en', enabled_locales: ['en', 'fr', 'nb-NO'] }

vi.mock('$lib/authContext.svelte', () => ({ getAuthContext: () => ({ config }) }))

describe('getLocalesContext().pickTranslation', () => {
  beforeEach(() => {
    config.default_locale = 'en'
    config.enabled_locales = ['en', 'fr', 'nb-NO']
  })

  it('takes the text written for the current locale', () => {
    const locales = getLocalesContext()

    expect(locales.pickTranslation({ en: 'Hello', fr: 'Bonjour' })).toBe('Bonjour')
  })

  it('falls back to the default locale, then to any enabled one', () => {
    const locales = getLocalesContext()

    expect(locales.pickTranslation({ en: 'Hello', 'nb-NO': 'Hei' })).toBe('Hello')
    expect(locales.pickTranslation({ 'nb-NO': 'Hei' })).toBe('Hei')
  })

  it('skips locales the instance does not offer', () => {
    config.enabled_locales = ['en', 'fr']
    const locales = getLocalesContext()

    expect(locales.pickTranslation({ da: 'Hej' })).toBeUndefined()
    expect(locales.pickTranslation({})).toBeUndefined()
  })
})
