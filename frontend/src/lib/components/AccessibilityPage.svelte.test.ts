// @vitest-environment jsdom

import { render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import AccessibilityPage from '../../routes/arene/accessibilite/+page.svelte'

const auth = {
  config: { platform_url: 'https://arena.example.test', platform_name: 'Plateforme de test' }
}

vi.mock('$lib/auth.svelte', () => ({ getAuthContext: () => auth }))

describe('Accessibility declaration', () => {
  it('uses the canonical deployment domain in the declaration', () => {
    const { container } = render(AccessibilityPage)

    expect(container.textContent).toContain('arena.example.test')
    expect(container.textContent).not.toContain('comparia.beta.gouv.fr')
  })

  it('falls back to the platform name when its URL is invalid', () => {
    auth.config.platform_url = '://invalid'
    const { container } = render(AccessibilityPage)

    expect(container.textContent).toContain('Plateforme de test')
    auth.config.platform_url = 'https://arena.example.test'
  })
})
