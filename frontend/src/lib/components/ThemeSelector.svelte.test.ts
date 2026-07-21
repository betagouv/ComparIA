import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ThemeSelector from './ThemeSelector.svelte'

describe('ThemeSelector', () => {
  const scheme = { scheme: 'system' }
  const dsfr = vi.fn(() => ({ scheme }))

  beforeEach(() => {
    scheme.scheme = 'system'
    dsfr.mockClear()
    vi.stubGlobal('dsfr', dsfr)
  })

  afterEach(() => {
    document.documentElement.removeAttribute('data-fr-scheme')
    vi.unstubAllGlobals()
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

    expect(dsfr).toHaveBeenCalledWith(document.documentElement)
    expect(scheme.scheme).toBe('light')
  })
})
