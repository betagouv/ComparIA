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

    expect(container.querySelector('#tab-account-panel')).toBeInTheDocument()
    expect(container.querySelector('#tab-about-panel')).not.toBeInTheDocument()

    await fireEvent.click(getByRole('tab', { name: 'À propos' }))

    expect(container.querySelector('#tab-account-panel')).not.toBeInTheDocument()
    expect(container.querySelector('#tab-about-panel')).toBeInTheDocument()
  })

  it('switches and focuses tabs with the keyboard', async () => {
    const { container, getByRole } = render(Tabs, {
      tabs: [
        { id: 'account', label: 'Compte', content: 'Contenu du compte' },
        { id: 'about', label: 'À propos', content: 'Contenu à propos' },
        { id: 'privacy', label: 'Confidentialité', content: 'Contenu confidentialité' }
      ],
      label: 'Rubriques'
    })

    const accountTab = getByRole('tab', { name: 'Compte' })
    const aboutTab = getByRole('tab', { name: 'À propos' })
    const privacyTab = getByRole('tab', { name: 'Confidentialité' })

    accountTab.focus()
    await fireEvent.keyDown(accountTab, { key: 'ArrowRight' })
    await Promise.resolve()
    expect(document.activeElement).toBe(aboutTab)
    expect(container.querySelector('#tab-about-panel')).toBeInTheDocument()

    await fireEvent.keyDown(aboutTab, { key: 'End' })
    await Promise.resolve()
    expect(document.activeElement).toBe(privacyTab)

    await fireEvent.keyDown(privacyTab, { key: 'Home' })
    await Promise.resolve()
    expect(document.activeElement).toBe(accountTab)

    await fireEvent.keyDown(accountTab, { key: 'ArrowLeft' })
    await Promise.resolve()
    expect(document.activeElement).toBe(privacyTab)
  })
})
