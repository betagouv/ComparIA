import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import Tabs from './Tabs.svelte'

describe('Tabs', () => {
  it('hides the inactive panel immediately when switching tabs', async () => {
    const { container, getByRole } = render(Tabs, {
      tabs: [
        { id: 'account', label: 'Compte', content: 'Contenu du compte' },
        { id: 'about', label: 'À propos', content: 'Contenu à propos' }
      ],
      label: 'Rubriques'
    })

    const accountPanel = container.querySelector('#tab-account-panel')
    const aboutPanel = container.querySelector('#tab-about-panel')

    expect(accountPanel).not.toHaveAttribute('hidden')
    expect(aboutPanel).toHaveAttribute('hidden')

    await fireEvent.click(getByRole('tab', { name: 'À propos' }))

    expect(accountPanel).toHaveAttribute('hidden')
    expect(aboutPanel).not.toHaveAttribute('hidden')
  })
})
