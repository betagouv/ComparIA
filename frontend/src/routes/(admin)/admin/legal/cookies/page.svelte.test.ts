import type { CookieBanner } from '$lib/generated/admin'
import { fireEvent, render, waitFor, within } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { PageData } from './$types'
import Page from './+page.svelte'

const mocks = vi.hoisted(() => ({ request: vi.fn(), toast: vi.fn() }))
vi.mock('$lib/fastapi-client', () => ({ api: { request: mocks.request } }))
vi.mock('$lib/helpers/useToast.svelte', () => ({ useToast: mocks.toast }))
vi.mock('$lib/authContext.svelte', () => ({
  getAuthContext: () => ({ config: { default_locale: 'fr', enabled_locales: ['fr', 'en'] } }),
  getPlatformName: () => 'Compar:IA',
  tryGetAuthContext: () => ({ config: { default_locale: 'fr', enabled_locales: ['fr', 'en'] } })
}))

const frBanner: CookieBanner = {
  title: 'Cookies sur ce site',
  description: 'Nous utilisons des cookies seulement si vous l’acceptez.',
  audience_measurement_label: 'Mesure d’audience',
  audience_measurement_description: 'Compter les visites.',
  remembered_settings_label: 'Réglages mémorisés',
  remembered_settings_description: 'Garder la langue et le thème.'
}

function renderPage(enabled = false) {
  return render(Page, {
    data: {
      settings: { cookie_banner_enabled: enabled },
      banners: { fr: structuredClone(frBanner) }
    } as unknown as PageData,
    params: {}
  })
}

function bodyOf(method: string) {
  const call = mocks.request.mock.calls.find(([, options]) => options?.method === method)
  return JSON.parse(call?.[1]?.body as string)
}

describe('cookie banner administration', () => {
  beforeEach(() => {
    mocks.request.mockReset()
    mocks.toast.mockReset()
    mocks.request.mockImplementation((_path: string, options?: RequestInit) =>
      Promise.resolve(options?.method === 'PATCH' ? { cookie_banner_enabled: true } : {})
    )
  })

  it('turns the banner on through the instance settings', async () => {
    const { getByRole } = renderPage()
    const toggle = getByRole('checkbox', { name: /Afficher le bandeau cookies/ })
    expect(toggle).not.toBeChecked()

    await fireEvent.click(toggle)

    await waitFor(() =>
      expect(mocks.request).toHaveBeenCalledWith(
        '/admin/settings',
        expect.objectContaining({ method: 'PATCH' })
      )
    )
    expect(bodyOf('PATCH')).toEqual({ cookie_banner_enabled: true })
    await waitFor(() => expect(toggle).toBeChecked())
  })

  it('previews the banner with its text and three buttons', async () => {
    const { getByLabelText, getByTestId } = renderPage()

    await fireEvent.input(getByLabelText('Titre du bandeau'), {
      target: { value: 'Vos cookies' }
    })

    const preview = getByTestId('cookie-banner-preview')
    await waitFor(() => expect(preview).toHaveTextContent('Vos cookies'))
    expect(preview).toHaveTextContent('Mesure d’audience')
    expect(preview).toHaveTextContent('Réglages mémorisés')
    for (const name of ['Tout accepter', 'Tout refuser', 'Choisir']) {
      expect(within(preview).getByRole('button', { name })).toBeInTheDocument()
    }
  })

  it('previews both kinds of cookie when they share a name', async () => {
    const { getByLabelText, getByTestId } = renderPage()

    await fireEvent.input(getByLabelText('Nom des réglages mémorisés'), {
      target: { value: 'Mesure d’audience' }
    })

    const items = getByTestId('cookie-banner-preview').querySelectorAll('li')
    await waitFor(() => expect(items[1]).toHaveTextContent('Mesure d’audience'))
    expect(items).toHaveLength(2)
  })

  it('saves the text and drops languages left empty', async () => {
    const { getByRole } = renderPage()

    await fireEvent.click(getByRole('button', { name: 'Enregistrer' }))

    await waitFor(() =>
      expect(mocks.request).toHaveBeenCalledWith(
        '/admin/legal/cookies',
        expect.objectContaining({ method: 'put' })
      )
    )
    expect(bodyOf('put')).toEqual({ fr: frBanner })
  })

  it('saves text written in a second language', async () => {
    const { getByRole, getByLabelText } = renderPage()

    await fireEvent.click(getByRole('radio', { name: /English/ }))
    await fireEvent.input(getByLabelText('Titre du bandeau'), {
      target: { value: 'Cookies on this site' }
    })
    await fireEvent.click(getByRole('button', { name: 'Enregistrer' }))

    await waitFor(() => expect(bodyOf('put').en.title).toBe('Cookies on this site'))
    expect(bodyOf('put').fr).toEqual(frBanner)
  })
})
