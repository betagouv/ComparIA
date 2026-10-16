import { overwriteGetLocale } from '$lib/i18n/runtime'
import { render } from '@testing-library/svelte'
import { afterEach, describe, expect, it, vi } from 'vitest'
import PauseNotice from './PauseNotice.svelte'

const state = vi.hoisted(() => ({
  auth: { user: null } as { user: { email: string } | null } | null,
  signedInFactor: 3 as number | undefined
}))

vi.mock('$lib/authContext.svelte', () => ({ tryGetAuthContext: () => state.auth }))
vi.mock('$lib/limits.svelte', () => ({
  getLimitsContext: () => ({
    get signedInFactor() {
      return state.signedInFactor
    }
  })
}))

const session = { scope: 'session' as const, resets_at: null }
const signIn = /Connectez-vous pour écrire jusqu'à/

afterEach(() => {
  state.auth = { user: null }
  state.signedInFactor = 3
  overwriteGetLocale(() => 'fr')
})

describe('PauseNotice', () => {
  it('offers sign-in to an anonymous person who spent their own allowance', () => {
    const view = render(PauseNotice, { pause: session })

    expect(view.getByText("Connectez-vous pour écrire jusqu'à 3 fois plus.")).toBeInTheDocument()
    // DSFR opens the arena's sign-in modal from it.
    const button = view.getByRole('button', { name: 'Se connecter' })
    expect(button).toHaveAttribute('aria-controls', 'fr-modal-signin')
    // "Fusionner" starts ticked from here: the conversation stays the person's.
    expect(button).toHaveAttribute('data-sign-in-merge')
  })

  it('says the factor in force, in the locale', () => {
    state.signedInFactor = 2.5
    overwriteGetLocale(() => 'en')
    const view = render(PauseNotice, { pause: session })

    expect(view.getByText('Sign in to write up to 2.5 times more.')).toBeInTheDocument()
    expect(view.getByRole('button', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('offers nothing when the network spent it: signing in would not help', () => {
    const view = render(PauseNotice, { pause: { scope: 'network', resets_at: null } })

    expect(view.queryByText(signIn)).toBeNull()
    expect(view.queryByRole('button', { name: 'Se connecter' })).toBeNull()
  })

  it('offers nothing to someone already signed in', () => {
    state.auth = { user: { email: 'a@example.org' } }
    const view = render(PauseNotice, { pause: session })

    expect(view.queryByText(signIn)).toBeNull()
  })

  it('offers nothing before the factor is known, or when it gives no more room', () => {
    state.signedInFactor = undefined
    expect(render(PauseNotice, { pause: session }).queryByText(signIn)).toBeNull()

    state.signedInFactor = 1
    expect(render(PauseNotice, { pause: session }).queryByText(signIn)).toBeNull()
  })
})
