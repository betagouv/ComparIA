import { isRedirect } from '@sveltejs/kit'
import { describe, expect, it } from 'vitest'
import { load as donneesPersonnelles } from './donnees-personnelles/+page.server'
import { load as modalites } from './modalites/+page.server'
import { load as terms } from './terms/+page.server'

function redirectOf(load: () => void) {
  try {
    load()
  } catch (error) {
    if (isRedirect(error)) return { status: error.status, location: error.location }
    throw error
  }
  throw new Error('the load did not redirect')
}

describe('legacy legal routes', () => {
  it.each([
    ['modalites', modalites, '/arene/modalites'],
    ['terms', terms, '/arene/modalites'],
    ['donnees-personnelles', donneesPersonnelles, '/arene/donnees-personnelles']
  ])('sends %s to its published page', (_name, load, location) => {
    expect(redirectOf(load)).toEqual({ status: 308, location })
  })
})
