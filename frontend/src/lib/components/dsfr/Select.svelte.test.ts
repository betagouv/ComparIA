import { render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import Select from './Select.svelte'

const options = [
  { value: 'a', label: 'A' },
  { value: 'b', label: 'B' }
]

describe('Select', () => {
  it('describes the field with its help text', () => {
    const { container, getByRole } = render(Select, {
      id: 'kind',
      selected: 'a',
      label: 'Type',
      help: 'Choisissez un type',
      options
    })

    expect(getByRole('combobox').getAttribute('aria-describedby')).toBe('kind-help')
    expect(container.querySelector('#kind-help')?.textContent).toBe('Choisissez un type')
  })

  it('reserves the hint line when asked without help text', () => {
    const { container, getByRole } = render(Select, {
      id: 'kind',
      selected: 'a',
      label: 'Type',
      reserveHintSpace: true,
      options
    })

    expect(getByRole('combobox').getAttribute('aria-describedby')).toBeNull()
    expect(container.querySelector('.fr-hint-text')?.getAttribute('aria-hidden')).toBe('true')
  })
})
