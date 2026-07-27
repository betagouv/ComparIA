import { render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import CategoryTextFields from './CategoryTextFields.svelte'

const labels = {
  titleLabel: 'Nom de la catégorie',
  descriptionLabel: 'Description',
  descriptionHint: 'Visible dans l’arène.',
  tooltipLabel: 'Information complémentaire',
  tooltipHint: 'Facultatif.',
  titleMaximumHint: '100 caractères maximum',
  descriptionMaximumHint: '300 caractères maximum',
  tooltipMaximumHint: '300 caractères maximum'
}

describe('CategoryTextFields', () => {
  it('matches the server limits and exposes them as field descriptions', () => {
    const { getByLabelText, container } = render(CategoryTextFields, {
      title: '',
      description: '',
      tooltip: '',
      ...labels
    })

    const title = getByLabelText(/Nom de la catégorie/)
    const description = getByLabelText(/Description/)
    const tooltip = getByLabelText(/Information complémentaire/)

    const accessibleDescription = (element: HTMLElement) =>
      element
        .getAttribute('aria-describedby')
        ?.split(' ')
        .map((id) => container.querySelector(`#${id}`)?.textContent?.trim())
        .filter(Boolean)
        .join(' ')

    expect(title.getAttribute('maxlength')).toBe('100')
    expect(accessibleDescription(title)).toBe('100 caractères maximum')
    expect(description.getAttribute('maxlength')).toBe('300')
    expect(accessibleDescription(description)).toBe('Visible dans l’arène. 300 caractères maximum')
    expect(tooltip.getAttribute('maxlength')).toBe('300')
    expect(accessibleDescription(tooltip)).toBe('Facultatif. 300 caractères maximum')
  })
})
