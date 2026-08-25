import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import Form from './Form.svelte'
import type { AnyFormItemProps } from '$lib/utils/form'

const linkList: AnyFormItemProps = {
  id: 'links',
  label: 'Links',
  component: 'fieldset-list',
  value: [],
  subProps: {
    id: 'link',
    label: 'Link',
    value: {},
    component: 'fieldset-item',
    subProps: [
      { id: 'text', label: 'Text', value: '', component: 'input', type: 'text', placeholder: '' }
    ]
  }
}

const modalities: AnyFormItemProps = {
  id: 'inputs',
  label: 'Modalities',
  component: 'checkbox-group',
  value: [],
  options: [
    { value: 'text', label: 'text' },
    { value: 'image', label: 'image' }
  ]
}

function renderForm(form: Record<string, any>) {
  return render(Form, {
    props: { id: 'llm', label: 'LLM', items: [modalities, linkList], form, onSubmit: () => {} }
  })
}

describe('Form', () => {
  // Creating a record starts from an empty object, so the list fields render
  // bound to a key that is not there yet.
  it('renders list fields the form has no key for', () => {
    const { container } = renderForm({})

    expect(container.querySelectorAll('#fieldset-links input')).toHaveLength(0)
    expect(container.querySelectorAll('input[type="checkbox"]')).toHaveLength(2)
  })

  it('adds a link to a form that had no links key', async () => {
    const form = $state<Record<string, any>>({})
    const { container, getByRole } = renderForm(form)

    await fireEvent.click(getByRole('button', { name: 'add' }))

    expect(container.querySelectorAll('#fieldset-links input')).toHaveLength(1)
    expect(form.links).toHaveLength(1)
  })

  it('ticks a checkbox on a form that had no key for the group', async () => {
    const form = $state<Record<string, any>>({})
    const { container } = renderForm(form)

    const [text, image] = [
      ...container.querySelectorAll<HTMLInputElement>('input[type="checkbox"]')
    ]
    await fireEvent.click(text)
    await fireEvent.click(image)
    expect(form.inputs).toEqual(['text', 'image'])

    await fireEvent.click(text)
    expect(form.inputs).toEqual(['image'])
  })
})
