import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import ModelFilterBuilder from './ModelFilterBuilder.svelte'

const catalogue = {
  llmChoices: [{ value: 'm1', label: 'Mistral Small', hint: 'Mistral AI' }],
  labChoices: [{ value: 'l1', label: 'Mistral AI' }],
  licenseChoices: [],
  tags: ['legal']
}
const lookups = {
  llms: new Map([['m1', 'Mistral Small']]),
  labs: new Map([['l1', 'Mistral AI']]),
  licenses: new Map()
}

function setup(value = {}) {
  return render(ModelFilterBuilder, { id: 'pool_a', value, catalogue, lookups })
}

describe('ModelFilterBuilder', () => {
  it('shows an empty filter as every model', () => {
    const { container } = setup()
    expect(container.querySelector('ul[aria-label]')).toBeNull()
  })

  it('lists the criteria set, and clears one from its chip', async () => {
    const { getByLabelText, getAllByRole } = setup({ params_max: 60, eu_hostable: true })
    const max = container(
      getByLabelText(/Maximum parameters|Paramètres maximum/, { selector: 'input' })
    )
    expect(max.value).toBe('60')

    const chips = getAllByRole('list')[0].querySelectorAll('li')
    expect(chips).toHaveLength(2)

    await fireEvent.click(chips[1].querySelector('button')!)
    expect(max.value).toBe('')
  })

  it('writes a typed number as a number and an emptied one as nothing', async () => {
    const { getByLabelText, getAllByRole } = setup()
    const min = container(
      getByLabelText(/Minimum parameters|Paramètres minimum/, { selector: 'input' })
    )

    await fireEvent.input(min, { target: { value: '100' } })
    expect(getAllByRole('list')[0].textContent).toContain('100')

    await fireEvent.input(min, { target: { value: '' } })
    expect(min.value).toBe('')
  })
})

function container(element: HTMLElement) {
  return element as HTMLInputElement
}
