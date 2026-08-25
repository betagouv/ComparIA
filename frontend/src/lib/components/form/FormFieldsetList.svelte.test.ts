import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import FormFieldsetList from './FormFieldsetList.svelte'

describe('FormFieldsetList', () => {
  it('adds a new item and keeps the add control out of form submission', async () => {
    const { container, getByRole } = render(FormFieldsetList, {
      props: {
        id: 'links',
        label: 'Links',
        value: [],
        component: 'fieldset-list',
        subProps: {
          id: 'link',
          label: 'Link',
          value: '',
          component: 'input',
          type: 'url',
          placeholder: ''
        }
      }
    })

    const addButton = getByRole('button', { name: 'add' })
    expect(addButton).toHaveAttribute('type', 'button')
    expect(container.querySelectorAll('input')).toHaveLength(0)

    await fireEvent.click(addButton)

    expect(container.querySelectorAll('input')).toHaveLength(1)
  })
})
