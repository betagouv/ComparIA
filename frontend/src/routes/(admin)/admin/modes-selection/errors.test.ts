import { ValidationError } from '$lib/fastapi-client'
import { m } from '$lib/i18n/messages'
import { updateFormDetailError, updateFormErrors } from '$lib/stores/form.svelte'
import { describe, expect, it } from 'vitest'
import { errorText, MODE_ERROR_FIELDS, MODE_ERRORS, requestErrorText } from './errors'

const options = { errorMessages: MODE_ERRORS, errorFields: MODE_ERROR_FIELDS }

describe('mode errors in the form', () => {
  it('puts a field error under the field of its pool', () => {
    const errors = {}
    updateFormErrors(
      new ValidationError([
        { loc: ['body', 'pool_a', 'top_ranked'], msg: 'x', type: 'greater_than_equal' }
      ]),
      errors,
      options
    )
    expect(errors).toEqual({ 'pool_a-top_ranked': m['admin.selectionModes.errors.tooSmall']() })
  })

  it('puts an error about two fields next to the one to change', () => {
    const errors = {}
    updateFormErrors(
      new ValidationError([
        { loc: ['body', 'pool_b'], msg: 'The minimum...', type: 'invalid_params_range' },
        { loc: ['body'], msg: 'The mode ends...', type: 'invalid_window' },
        { loc: ['body', 'label'], msg: 'label_missing_default_locale', type: 'value_error' }
      ]),
      errors,
      options
    )
    expect(errors).toEqual({
      'pool_b-params_max': m['admin.selectionModes.errors.paramsRange'](),
      ends_at: m['admin.selectionModes.errors.window'](),
      label: m['admin.selectionModes.errors.labelDefaultLocale']()
    })
  })
})

describe('mode request errors in the form', () => {
  it('shows a known detail on its field and leaves others to the caller', () => {
    const errors = {}
    const taken = Object.assign(new Error('409'), { detail: 'mode_key_taken' })
    expect(updateFormDetailError(taken, errors, options)).toBe(true)
    expect(errors).toEqual({ key: m['admin.selectionModes.errors.keyTaken']() })
    expect(updateFormDetailError(new Error('boom'), errors, options)).toBe(false)
  })
})

describe('requestErrorText', () => {
  it('translates server keys and leaves unknown text as it is', () => {
    const error = (detail: string) => Object.assign(new Error(detail), { detail })
    expect(requestErrorText(error('last_enabled_mode'))).toBe(
      m['admin.selectionModes.errors.lastEnabled']()
    )
    expect(requestErrorText(error('Something else'))).toBe('Something else')
    expect(errorText({ msg: 'x', type: 'invalid_window' })).toBe(
      m['admin.selectionModes.errors.window']()
    )
    expect(errorText({ msg: 'Something else', type: 'other' })).toBe('Something else')
  })
})
