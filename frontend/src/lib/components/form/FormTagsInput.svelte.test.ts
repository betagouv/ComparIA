import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import FormTagsInput from './FormTagsInput.svelte'

function setup(value: string[] | null = ['legal']) {
  return render(FormTagsInput, {
    id: 'tags',
    label: 'Tags',
    component: 'tags',
    suggestions: ['legal', 'medical'],
    value
  })
}

describe('FormTagsInput', () => {
  it('adds what is typed on Enter or comma, once each', async () => {
    const { getByLabelText, getAllByRole } = setup()
    const input = getByLabelText('Tags', { selector: 'input' }) as HTMLInputElement

    await fireEvent.input(input, { target: { value: 'sovereign, legal' } })
    await fireEvent.keyDown(input, { key: 'Enter' })

    expect(getAllByRole('listitem').map((item) => item.textContent?.trim())).toEqual([
      'legal',
      'sovereign'
    ])
    expect(input.value).toBe('')
  })

  it('removes a value from its button and moves focus to the next one', async () => {
    const { getAllByRole, queryAllByRole } = setup(['legal', 'medical'])
    const [first] = getAllByRole('button')

    await fireEvent.click(first)

    expect(queryAllByRole('listitem')).toHaveLength(1)
    expect(document.activeElement).toBe(getAllByRole('button')[0])
  })

  it('starts empty from a null value and offers only unused suggestions', () => {
    const { container, queryAllByRole } = setup(null)
    expect(queryAllByRole('listitem')).toHaveLength(0)
    const options = [...container.querySelectorAll('datalist option')].map(
      (option) => (option as HTMLOptionElement).value
    )
    expect(options).toEqual(['legal', 'medical'])
  })
})
