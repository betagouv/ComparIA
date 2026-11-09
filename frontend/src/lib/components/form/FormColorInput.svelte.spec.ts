import { fireEvent, render, screen } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import FormColorInput from './FormColorInput.svelte'

describe('FormColorInput', () => {
  it('synchronises the hexadecimal field with the native colour picker', async () => {
    const { container } = render(FormColorInput, {
      id: 'primary-light',
      label: 'Couleur primaire (thème clair)',
      help: 'Format attendu : #RRGGBB.',
      value: '#6464F3'
    })
    const textInput = container.querySelector<HTMLInputElement>('#primary-light')
    const picker = container.querySelector<HTMLInputElement>('input[type="color"]')

    expect(picker?.value).toBe('#6464f3')
    expect(textInput?.checkValidity()).toBe(true)
    await fireEvent.input(textInput!, { target: { value: '#112233' } })
    expect(picker?.value).toBe('#112233')
  })

  it('lets an incomplete value through so the form can show its own error', async () => {
    const { container } = render(FormColorInput, {
      id: 'primary-light',
      label: 'Couleur primaire (thème clair)',
      help: 'Format attendu : #RRGGBB.',
      value: '#6464F3'
    })
    const textInput = container.querySelector<HTMLInputElement>('#primary-light')

    await fireEvent.input(textInput!, { target: { value: '#12' } })

    expect(textInput?.checkValidity()).toBe(true)
  })

  it('connects an explicit validation error to both controls', () => {
    const { container } = render(FormColorInput, {
      id: 'primary-dark',
      label: 'Couleur primaire (thème sombre)',
      help: 'Format attendu : #RRGGBB.',
      value: '#161616',
      errors: { 'primary-dark': 'Contraste insuffisant.' }
    })
    const textInput = container.querySelector<HTMLInputElement>('#primary-dark')
    const picker = container.querySelector<HTMLInputElement>('input[type="color"]')
    const error = screen.getByText('Contraste insuffisant.')

    expect(textInput?.getAttribute('aria-invalid')).toBe('true')
    expect(textInput?.getAttribute('aria-describedby')).toBe('primary-dark-messages')
    expect(picker?.getAttribute('aria-describedby')).toBe('primary-dark-messages')
    expect(error.closest('[aria-live="polite"]')).not.toBeNull()
  })
})
