import { render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import LegalDocument from './LegalDocument.svelte'

describe('LegalDocument', () => {
  it('shows the version above the body and drops the repeated title', () => {
    const { container, getByRole } = render(LegalDocument, {
      version: '2-juillet',
      effectiveAt: '2026-07-01T00:00:00',
      content: '# Conditions\n\n## Objet\n\nCe que fait la plateforme.'
    })

    expect(container.textContent).toContain('2-juillet')
    expect(getByRole('heading', { name: 'Objet' })).toBeTruthy()
    expect(container.querySelector('h1')).toBeNull()
  })
})
