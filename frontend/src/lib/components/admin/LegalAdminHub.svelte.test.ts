import { render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import Page from '../../../routes/(admin)/admin/legal/+page.svelte'

describe('Legal administration hub', () => {
  it('presents separate compact navigation groups without cards or tabs', () => {
    const { container, getByRole } = render(Page)

    expect(getByRole('heading', { name: 'Parcours d’acceptation' })).toBeTruthy()
    expect(getByRole('heading', { name: 'Documents juridiques' })).toBeTruthy()
    expect(getByRole('link', { name: 'Parcours de participation' }).getAttribute('href')).toBe(
      '/admin/conditions-participation'
    )
    expect(getByRole('link', { name: 'Conditions d’utilisation' }).getAttribute('href')).toBe(
      '/admin/legal/conditions'
    )
    expect(getByRole('link', { name: 'Politique de confidentialité' }).getAttribute('href')).toBe(
      '/admin/legal/confidentialite'
    )
    expect(container.querySelector('.fr-card')).toBeNull()
    expect(container.querySelector('.fr-badge')).toBeNull()
    expect(container.querySelector('[role="tablist"]')).toBeNull()
  })
})
