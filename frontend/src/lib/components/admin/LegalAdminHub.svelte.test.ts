import { render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import Page from '../../../routes/(admin)/admin/legal/+page.svelte'

describe('Legal administration hub', () => {
  it('links to each legal administration area', () => {
    const { getByRole } = render(Page)

    expect(getByRole('heading', { name: 'Parcours d’acceptation' })).toBeTruthy()
    expect(getByRole('heading', { name: 'Documents juridiques' })).toBeTruthy()
    const links = [
      getByRole('link', { name: 'Parcours de participation' }),
      getByRole('link', { name: 'Conditions d’utilisation' }),
      getByRole('link', { name: 'Politique de confidentialité' })
    ]
    expect(links[0].getAttribute('href')).toBe('/admin/conditions-participation')
    expect(links[1].getAttribute('href')).toBe('/admin/legal/conditions')
    expect(links[2].getAttribute('href')).toBe('/admin/legal/confidentialite')
  })
})
