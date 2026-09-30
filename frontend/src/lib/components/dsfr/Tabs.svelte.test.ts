import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import Tabs from './Tabs.svelte'

describe('Tabs', () => {
  it('updates the selected tab and panel', async () => {
    const { container, getByRole } = render(Tabs, {
      tabs: [
        { id: 'add', label: 'Ajouter', content: 'Formulaire' },
        { id: 'manage', label: 'Gérer', content: 'Liste' }
      ],
      label: 'Catégories'
    })

    const addTab = getByRole('tab', { name: 'Ajouter' })
    const manageTab = getByRole('tab', { name: 'Gérer' })

    expect(addTab).toHaveAttribute('aria-selected', 'true')
    expect(manageTab).toHaveAttribute('aria-selected', 'false')
    expect(getByRole('tabpanel', { name: 'Ajouter' })).not.toHaveAttribute('hidden')
    expect(container.querySelector('#tab-manage-panel')).toHaveAttribute('hidden')

    await fireEvent.click(manageTab)

    expect(addTab).toHaveAttribute('aria-selected', 'false')
    expect(manageTab).toHaveAttribute('aria-selected', 'true')
    expect(getByRole('tabpanel', { name: 'Gérer' })).toHaveClass('fr-tabs__panel--selected')
    expect(container.querySelector('#tab-add-panel')).toHaveAttribute('hidden')
  })

  it('moves between tabs with the arrow, home and end keys', async () => {
    const { getByRole } = render(Tabs, {
      tabs: [
        { id: 'account', label: 'Compte', content: 'Contenu du compte' },
        { id: 'about', label: 'À propos', content: 'Contenu à propos' },
        { id: 'privacy', label: 'Confidentialité', content: 'Contenu confidentialité' }
      ],
      label: 'Rubriques'
    })

    const account = getByRole('tab', { name: 'Compte' })
    const about = getByRole('tab', { name: 'À propos' })
    const privacy = getByRole('tab', { name: 'Confidentialité' })

    account.focus()
    await fireEvent.keyDown(account, { key: 'ArrowRight' })
    expect(document.activeElement).toBe(about)

    await fireEvent.keyDown(about, { key: 'End' })
    expect(document.activeElement).toBe(privacy)

    await fireEvent.keyDown(privacy, { key: 'Home' })
    expect(document.activeElement).toBe(account)

    await fireEvent.keyDown(account, { key: 'ArrowLeft' })
    expect(document.activeElement).toBe(privacy)
    expect(privacy).toHaveAttribute('aria-selected', 'true')
  })
})
