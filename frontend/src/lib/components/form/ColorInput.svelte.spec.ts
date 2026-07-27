import { fireEvent, render, screen } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import ColorInput from './ColorInput.svelte'

describe('ColorInput', () => {
  it('synchronises the hexadecimal field with the native colour picker', async () => {
    const { container } = render(ColorInput, {
      id: 'primary-light',
      label: 'Couleur primaire (thème clair)',
      hint: 'Format attendu : #RRGGBB.',
      value: '#6464F3'
    })
    const textInput = container.querySelector<HTMLInputElement>('#primary-light-text')
    const picker = container.querySelector<HTMLInputElement>('input[type="color"]')

    expect(picker?.value).toBe('#6464f3')
    expect(textInput?.pattern).toBe('#[0-9A-Fa-f]{6}')
    expect(textInput?.checkValidity()).toBe(true)
    await fireEvent.input(textInput!, { target: { value: '#112233' } })
    expect(picker?.value).toBe('#112233')
  })

  it('connects an explicit validation error to both controls', () => {
    const { container } = render(ColorInput, {
      id: 'primary-dark',
      label: 'Couleur primaire (thème sombre)',
      hint: 'Format attendu : #RRGGBB.',
      value: '#161616',
      error: 'Contraste insuffisant.'
    })
    const textInput = container.querySelector<HTMLInputElement>('#primary-dark-text')
    const picker = container.querySelector<HTMLInputElement>('input[type="color"]')
    const error = screen.getByText('Contraste insuffisant.')

    expect(textInput?.getAttribute('aria-invalid')).toBe('true')
    expect(textInput?.getAttribute('aria-describedby')).toBe('primary-dark-messages')
    expect(picker?.getAttribute('aria-describedby')).toBe('primary-dark-messages')
    expect(error.closest('[aria-live="polite"]')).not.toBeNull()
  })
})
