import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { afterEach, describe, expect, it } from 'vitest'
import ThemeSelector from './ThemeSelector.svelte'

describe('ThemeSelector', () => {
  afterEach(() => {
    document.documentElement.removeAttribute('data-fr-scheme')
  })

  it('renders a directly accessible theme select', () => {
    const { getByRole, queryByRole } = render(ThemeSelector, { variant: 'select' })

    const select = getByRole('combobox', { name: "Paramètres d'affichage" })
    expect(select).toBeTruthy()
    expect(select.textContent).toContain('Thème clair')
    expect(select.textContent).toContain('Thème sombre')
    expect(select.textContent).toContain('Système')
    expect(queryByRole('dialog')).toBeNull()
  })

  it('uses the current scheme and applies a selected theme', async () => {
    document.documentElement.setAttribute('data-fr-scheme', 'dark')
    const { getByRole } = render(ThemeSelector, { variant: 'select' })
    const select = getByRole('combobox', {
      name: "Paramètres d'affichage"
    }) as HTMLSelectElement

    await waitFor(() => expect(select.value).toBe('dark'))
    await fireEvent.change(select, { target: { value: 'light' } })

    expect(document.documentElement.getAttribute('data-fr-scheme')).toBe('light')
  })
})
