import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import Tabs from './Tabs.svelte'

describe('Tabs', () => {
  it('updates the selected tab and panel', async () => {
    const { getByRole } = render(Tabs, {
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

    await fireEvent.click(manageTab)

    expect(addTab).toHaveAttribute('aria-selected', 'false')
    expect(manageTab).toHaveAttribute('aria-selected', 'true')
    expect(getByRole('tabpanel', { name: 'Gérer' })).toHaveClass('fr-tabs__panel--selected')
  })
})
