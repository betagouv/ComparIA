/**
 * Accessibility regression tests for the shared building blocks.
 *
 * Every case here stands for a defect that was actually shipped and found in
 * the RGAA audit of August 2026. Rendering a
 * component twice is not padding: the ids that collided on the reveal screen
 * were unique inside their component and only clashed once two models were
 * on screen at once.
 */
import { render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import { expectAccessible, expectNoDanglingAriaRefs, expectNoDuplicateIds } from '$lib/testing/a11y'
import Badge from './Badge.svelte'
import Icon from './Icon.svelte'
import Input from './Input.svelte'
import Toggle from './Toggle.svelte'

describe('Icon', () => {
  it('carries a name as an image so it is not dropped', async () => {
    const { container } = render(Icon, { icon: 'i-ri-check-line', 'aria-label': 'Terminé' })
    const span = container.querySelector('span')!

    // aria-label on a generic span is prohibited and ignored; role="img" is
    // what makes the name survive.
    expect(span.getAttribute('role')).toBe('img')
    expect(span.getAttribute('aria-hidden')).toBeNull()
    await expectAccessible(container)
  })

  it('hides itself when it has no name, being a decorative glyph', () => {
    const { container } = render(Icon, { icon: 'i-ri-check-line' })
    const span = container.querySelector('span')!

    expect(span.getAttribute('aria-hidden')).toBe('true')
    expect(span.getAttribute('role')).toBeNull()
  })

  it('does not override an explicit aria-hidden', () => {
    const { container } = render(Icon, {
      icon: 'i-ri-check-line',
      'aria-label': 'Terminé',
      'aria-hidden': 'true'
    })

    expect(container.querySelector('span')!.getAttribute('aria-hidden')).toBe('true')
  })
})

describe('Input', () => {
  it('labels the field and keeps the live region mounted', async () => {
    const { container } = render(Input, { id: 'email', value: '', label: 'Adresse électronique' })

    expect(container.querySelector('label')!.getAttribute('for')).toBe('email')
    // Present even with no error: a live region that appears at the same
    // moment as its message is not announced.
    expect(container.querySelector('#input-email-messages')).not.toBeNull()
    expectNoDanglingAriaRefs(container)
    await expectAccessible(container)
  })

  it('marks the field invalid and points at the message when it errors', async () => {
    const { container } = render(Input, {
      id: 'email',
      value: '',
      label: 'Adresse électronique',
      error: 'Saisissez une adresse valide, par exemple nom@domaine.fr'
    })
    const input = container.querySelector('input')!

    expect(input.getAttribute('aria-invalid')).toBe('true')
    expect(input.getAttribute('aria-describedby')).toBe('input-email-messages')
    expectNoDanglingAriaRefs(container)
    await expectAccessible(container)
  })
})

describe('Toggle', () => {
  it('only describes itself when there is a hint to point at', () => {
    const { container } = render(Toggle, { id: 'web-search', value: false, label: 'Recherche web' })

    expect(container.querySelector('input')!.getAttribute('aria-describedby')).toBeNull()
    expectNoDanglingAriaRefs(container)
  })

  it('links the hint when one is given', () => {
    const { container } = render(Toggle, {
      id: 'web-search',
      value: false,
      label: 'Recherche web',
      help: 'Interroge le web avant de répondre'
    })

    expect(container.querySelector('input')!.getAttribute('aria-describedby')).toBe(
      'toggle-hint-web-search'
    )
    expectNoDanglingAriaRefs(container)
  })
})

describe('Badge', () => {
  // The reveal screen shipped nineteen duplicate ids because the spread sat
  // after the id and silently overrode it.
  it('lets an explicit id win over the one carried in the spread', () => {
    const { container } = render(Badge, {
      id: 'unique-per-model',
      text: 'Licence libre',
      // what getModelCards puts on a badge
      ...{ variant: 'green' as const }
    })

    expect(container.querySelector('.fr-badge')!.id).toBe('unique-per-model')
  })

  it('keeps ids apart when the same badge is rendered twice', () => {
    const { container: first } = render(Badge, { id: 'model-a-badge-0', text: 'Licence libre' })
    const { container: second } = render(Badge, { id: 'model-b-badge-0', text: 'Licence libre' })

    const wrapper = document.createElement('div')
    wrapper.append(first.cloneNode(true), second.cloneNode(true))
    expectNoDuplicateIds(wrapper)
  })
})
