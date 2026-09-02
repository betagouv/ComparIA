import type { AnyFormItemProps } from '$lib/utils/form'
import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import FormFieldsetList from './FormFieldsetList.svelte'

const linkSubProps: AnyFormItemProps = {
  id: 'link',
  label: 'Link',
  value: {},
  component: 'fieldset-item',
  subProps: [
    { id: 'text', label: 'Text', value: '', component: 'input', type: 'text', placeholder: '' },
    { id: 'url', label: 'Url', value: '', component: 'input', type: 'url', placeholder: '' }
  ]
}

const textSubProps: AnyFormItemProps = {
  id: 'tag',
  label: 'Tag',
  value: '',
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
