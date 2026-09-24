import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import type { FormFieldsetItemProps, FormInputProps } from '.'
import FormFieldsetList from './FormFieldsetList.svelte'

const linkSubProps: FormFieldsetItemProps = {
  id: 'link',
  label: 'Link',
  component: 'fieldset-item',
  subProps: [
    { id: 'text', label: 'Text', component: 'input', type: 'text', placeholder: '' },
    { id: 'url', label: 'Url', component: 'input', type: 'url', placeholder: '' }
  ]
}

const textSubProps: FormInputProps = {
  id: 'tag',
  label: 'Tag',
  component: 'input',
  type: 'text',
  placeholder: ''
}

describe('FormFieldsetList', () => {
  it('adds an item when the parent holds no value yet', async () => {
    // The admin form starts empty on create, so value arrives undefined.
    const { container, getByRole } = render(FormFieldsetList, {
      props: { id: 'links', label: 'Links', component: 'fieldset-list', subProps: linkSubProps }
    })

    expect(container.querySelectorAll('input')).toHaveLength(0)

    await fireEvent.click(getByRole('button', { name: 'add' }))

    expect(container.querySelectorAll('input')).toHaveLength(2)
  })

  it('removes the item at the clicked index', async () => {
    const { container, getAllByRole } = render(FormFieldsetList, {
      props: {
        id: 'tags',
        label: 'Tags',
        value: ['a', 'b', 'c'],
        component: 'fieldset-list',
        subProps: textSubProps
      }
    })

    await fireEvent.click(getAllByRole('button', { name: 'delete' })[1])

    const values = [...container.querySelectorAll('input')].map((i) => i.value)
    expect(values).toEqual(['a', 'c'])
  })
})
