import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import CategoryIconPicker from './CategoryIconPicker.svelte'

const options = [
  { value: 'i-ri-lightbulb-line', label: 'Idée' },
  { value: 'i-ri-question-answer-line', label: 'Discussion' }
]

describe('CategoryIconPicker', () => {
  it('exposes each Remix icon as an accessible radio option', () => {
    const { getByRole, container } = render(CategoryIconPicker, {
      id: 'category-icon',
      label: 'Icône',
      options,
      value: options[0].value
    })

    expect(getByRole('group', { name: 'Icône' })).toBeTruthy()
    expect((getByRole('radio', { name: 'Idée' }) as HTMLInputElement).checked).toBe(true)
    expect((getByRole('radio', { name: 'Discussion' }) as HTMLInputElement).checked).toBe(false)
    expect(container.querySelector('.i-ri-lightbulb-line')).not.toBeNull()
    expect(container.querySelector('.i-ri-question-answer-line')).not.toBeNull()
    expect(container.querySelector('.flex.flex-wrap')).not.toBeNull()
    expect(container.querySelector('label')?.className).toContain('size-12')
  })

  it('selects an icon and reports the new value', async () => {
    const onchange = vi.fn()
    const { getByRole } = render(CategoryIconPicker, {
      id: 'category-icon',
      label: 'Icône',
      options,
      value: options[0].value,
      onchange
    })

    await fireEvent.click(getByRole('radio', { name: 'Discussion' }))

    expect((getByRole('radio', { name: 'Discussion' }) as HTMLInputElement).checked).toBe(true)
    expect(onchange).toHaveBeenCalledWith('i-ri-question-answer-line')
  })
})
