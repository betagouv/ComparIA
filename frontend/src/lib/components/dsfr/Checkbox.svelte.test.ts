import { render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import Checkbox from './Checkbox.svelte'

describe('Checkbox', () => {
  it('describes the input with its help text and links', () => {
    const { getByRole } = render(Checkbox, {
      id: 'cgu',
      checked: false,
      label: 'J’accepte',
      help: 'Obligatoire',
      links: [
        { label: 'Conditions', href: '/arene/modalites' },
        { label: 'Externe', href: 'https://example.test/cgu' }
      ]
    })

    const input = getByRole('checkbox')
    expect(input.getAttribute('aria-describedby')).toBe('cgu-help cgu-links')
    expect(input.getAttribute('aria-invalid')).toBeNull()
    expect(getByRole('link', { name: 'Conditions' })).toBeTruthy()
  })

  it('drops links with an unsafe href', () => {
    const { queryByRole } = render(Checkbox, {
      id: 'cgu',
      checked: false,
      label: 'J’accepte',
      links: [
        { label: 'Piège', href: 'javascript:alert(1)' },
        { label: 'Protocole', href: 'http://example.test/cgu' }
      ]
    })

    expect(queryByRole('link')).toBeNull()
  })

  it('points to the error message when invalid', () => {
    const { container, getByRole } = render(Checkbox, {
      id: 'cgu',
      checked: false,
      label: 'J’accepte',
      error: 'Champ requis'
    })

    const input = getByRole('checkbox')
    expect(input.getAttribute('aria-describedby')).toBe('cgu-error-messages')
    expect(input.getAttribute('aria-invalid')).toBe('true')
    expect(container.querySelector('#cgu-error-message')?.textContent?.trim()).toBe('Champ requis')
  })
})
