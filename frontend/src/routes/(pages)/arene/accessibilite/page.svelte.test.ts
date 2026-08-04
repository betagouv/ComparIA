import { render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import AccessibilityPage from './+page.svelte'

const auth = {
  config: { platform_url: 'https://arene.example.test', platform_name: 'Arène de test' }
}

vi.mock('$lib/auth.svelte', () => ({ getAuthContext: () => auth }))

describe('Accessibility declaration', () => {
  it('names the domain it applies to', () => {
    const { container } = render(AccessibilityPage)

    expect(container.textContent).toContain('arene.example.test')
    expect(container.textContent).not.toContain('comparia.beta.gouv.fr')
  })

  it('falls back to the platform name when the URL is unusable', () => {
    auth.config.platform_url = 'not a url'
    const { container } = render(AccessibilityPage)

    expect(container.textContent).toContain('Arène de test')
  })
})
