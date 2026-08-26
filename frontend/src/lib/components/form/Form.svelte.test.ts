import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import Form from './Form.svelte'
import type { AnyFormItemProps } from '$lib/utils/form'

const navigation = vi.hoisted(() => ({ before: undefined as ((nav: any) => void) | undefined }))
vi.mock('$app/navigation', () => ({
  beforeNavigate: (callback: (nav: any) => void) => (navigation.before = callback)
}))

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

function renderForm(form: Record<string, any>, isDirty = false) {
  return render(Form, {
    props: {
      id: 'llm',
      label: 'LLM',
      items: [modalities, linkList],
      form,
      isDirty,
      onSubmit: () => {}
    }
  })
}

describe('Form', () => {
  it('submits through the API handler without native navigation', async () => {
    const onSubmit = vi.fn()
    const { container } = render(Form, {
      props: { id: 'llm', label: 'LLM', items: [], form: {}, onSubmit }
    })
    const event = new SubmitEvent('submit', { bubbles: true, cancelable: true })

    container.querySelector('form')!.dispatchEvent(event)

    expect(event.defaultPrevented).toBe(true)
    expect(onSubmit).toHaveBeenCalledOnce()
  })

  it('uses the API handler when the save button is clicked', async () => {
    const onSubmit = vi.fn()
    const { getByRole } = render(Form, {
      props: { id: 'llm', label: 'LLM', items: [], form: {}, onSubmit }
    })

    await fireEvent.click(getByRole('button', { name: 'Enregistrer' }))

    expect(onSubmit).toHaveBeenCalledOnce()
  })

  it('does not make hidden generated fields browser-required', () => {
    const hiddenId = {
      id: 'id',
      label: 'Id',
      component: 'input',
      type: 'text',
      hidden: true,
      required: false,
      value: ''
    } as AnyFormItemProps
    const { container } = render(Form, {
      props: { id: 'lab', label: 'Lab', items: [hiddenId], form: {}, onSubmit: () => {} }
    })

    expect(container.querySelector('#id')).not.toHaveAttribute('required')
  })

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

  it('cancels in-app navigation when dirty changes are not confirmed', () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const cancel = vi.fn()
    renderForm({}, true)

    navigation.before?.({ type: 'link', cancel })

    expect(confirm).toHaveBeenCalled()
    expect(cancel).toHaveBeenCalled()
    confirm.mockRestore()
  })

  it('does not guard navigation when the form is clean', () => {
    const confirm = vi.spyOn(window, 'confirm')
    const cancel = vi.fn()
    renderForm({}, false)

    navigation.before?.({ type: 'link', cancel })

    expect(confirm).not.toHaveBeenCalled()
    expect(cancel).not.toHaveBeenCalled()
    confirm.mockRestore()
  })
})
