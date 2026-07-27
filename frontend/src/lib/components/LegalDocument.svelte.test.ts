import { render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import LegalDocument from './LegalDocument.svelte'

const { getLocale } = vi.hoisted(() => ({ getLocale: vi.fn(() => 'fr') }))

vi.mock('$lib/i18n/runtime', async (importOriginal) => ({
  ...(await importOriginal<object>()),
  getLocale
}))

const document = {
  version: '2-juillet',
  effectiveAt: '2026-07-01T00:00:00Z',
  content: '# Conditions\n\n## Objet\n\nCe que fait la plateforme.'
}

describe('LegalDocument', () => {
  it('shows the version above the body and drops the repeated title', () => {
    getLocale.mockReturnValue('fr')

    const { container, getByRole } = render(LegalDocument, { ...document, locale: 'fr' })

    expect(container.textContent).toContain('2-juillet')
    expect(getByRole('heading', { name: 'Objet' })).toBeTruthy()
    expect(container.querySelector('h1')).toBeNull()
  })

  it('dates the entry into force in Paris whatever the machine runs on', () => {
    getLocale.mockReturnValue('fr')

    // 01:30 in Paris the next day. Left to the host zone this reads 27 juillet
    // under UTC and 28 juillet in Paris, so the two would disagree on hydration.
    const { container } = render(LegalDocument, {
      ...document,
      effectiveAt: '2026-07-27T23:30:00Z',
      locale: 'fr'
    })

    expect(container.textContent).toContain('28 juillet 2026')
  })

  it('says so when the reader gets the French document instead of a translation', () => {
    getLocale.mockReturnValue('da')

    const { container } = render(LegalDocument, { ...document, locale: 'fr' })

    expect(container.querySelector('.fr-alert')?.textContent).toContain('français')
  })

  it('stays quiet when the document is in the requested language', () => {
    getLocale.mockReturnValue('fr')

    const { container } = render(LegalDocument, { ...document, locale: 'fr' })

    expect(container.querySelector('.fr-alert')).toBeNull()
  })
})
