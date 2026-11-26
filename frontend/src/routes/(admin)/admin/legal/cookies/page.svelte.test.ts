import type { CookieBanner } from '$lib/generated/admin'
import { fireEvent, render, waitFor, within } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { PageData, PageProps } from './$types'
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
  title: 'Mesure d’audience',
  description: 'Nous utilisons des cookies seulement si vous l’acceptez.'
}

const ownMatomo = { matomo_url: 'https://stats.example.org/matomo', matomo_site_id: '12' }
const serverMatomo = { MATOMO_URL: 'https://server-stats.example.org', MATOMO_ID: '3' }
const noServerMatomo = { MATOMO_URL: '', MATOMO_ID: '' }

function renderPage(
  enabled = false,
  matomoEnabled: boolean | null = null,
  stored: { matomo_url?: string; matomo_site_id?: string } = {},
  server: { MATOMO_URL: string; MATOMO_ID: string } = serverMatomo
) {
  return render(Page, {
    data: {
      settings: {
        cookie_banner_enabled: enabled,
        matomo_enabled: matomoEnabled,
        matomo_url: null,
        matomo_site_id: null,
        ...stored
      },
      banners: { fr: structuredClone(frBanner) },
      serverMatomo: server
    } as unknown as PageData,
    params: {}
  } as PageProps)
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
      Promise.resolve(
        options?.method === 'PATCH'
          ? { cookie_banner_enabled: true, ...JSON.parse(options.body as string) }
          : {}
      )
    )
  })

  it('names the page after both cookies and audience measurement', () => {
    const { getByRole } = renderPage()

    expect(getByRole('heading', { level: 1 })).toHaveTextContent('Cookies et mesure d’audience')
  })

  it.each([
    ['the server setting', null, /^Réglage du serveur/],
    ['on', true, 'Activée, avec mon Matomo'],
    ['off', false, 'Désactivée']
  ])('shows audience measurement on %s', (_case, matomoEnabled, checked) => {
    const { getByRole } = renderPage(false, matomoEnabled, ownMatomo)
    const group = getByRole('group', { name: /Mesure d’audience/ })

    expect(within(group).getAllByRole('radio')).toHaveLength(3)
    expect(within(group).getByRole('radio', { name: checked })).toBeChecked()
  })

  it.each([
    [
      'its address and site id',
      serverMatomo,
      'Actuellement activée : server-stats.example.org, site 3'
    ],
    ['no Matomo', noServerMatomo, 'Actuellement : aucune mesure d’audience']
  ])('says what the server setting means when the server has %s', (_case, server, means) => {
    const { getByRole } = renderPage(false, false, ownMatomo, server)

    expect(getByRole('radio', { name: /^Réglage du serveur/ })).toHaveAccessibleName(
      `Réglage du serveur ${means}`
    )
  })

  it.each([
    ['the server setting', null],
    ['off', false]
  ])('hides the Matomo address and site id on %s', (_case, matomoEnabled) => {
    const { queryByLabelText } = renderPage(false, matomoEnabled, ownMatomo)

    expect(queryByLabelText(/Adresse de Matomo/)).not.toBeInTheDocument()
    expect(queryByLabelText(/Identifiant du site/)).not.toBeInTheDocument()
  })

  it('shows the stored address and site id when on', () => {
    const { getByLabelText } = renderPage(false, true, ownMatomo)

    expect(getByLabelText(/Adresse de Matomo/)).toHaveValue('https://stats.example.org/matomo')
    expect(getByLabelText(/Identifiant du site/)).toHaveValue('12')
  })

  it('switches on with the address and site id typed in', async () => {
    const { getByRole, getByLabelText } = renderPage()

    await fireEvent.click(getByRole('radio', { name: 'Activée, avec mon Matomo' }))
    expect(mocks.request).not.toHaveBeenCalled()
    await fireEvent.input(getByLabelText(/Adresse de Matomo/), {
      target: { value: 'https://stats.example.org/matomo/' }
    })
    await fireEvent.input(getByLabelText(/Identifiant du site/), { target: { value: '12' } })
    mocks.request.mockResolvedValueOnce({ matomo_enabled: true, ...ownMatomo })
    await fireEvent.click(getByRole('button', { name: 'Activer la mesure d’audience' }))

    await waitFor(() => expect(mocks.toast).toHaveBeenCalled())
    expect(bodyOf('PATCH')).toEqual({
      matomo_enabled: true,
      matomo_url: 'https://stats.example.org/matomo/',
      matomo_site_id: '12'
    })
    expect(getByLabelText(/Adresse de Matomo/)).toHaveValue('https://stats.example.org/matomo')
    expect(getByRole('radio', { name: 'Activée, avec mon Matomo' })).toBeChecked()
  })

  it('keeps the stored address and site id when switched off', async () => {
    const { getByRole } = renderPage(false, true, ownMatomo)

    await fireEvent.click(getByRole('radio', { name: 'Désactivée' }))

    await waitFor(() => expect(mocks.toast).toHaveBeenCalled())
    expect(bodyOf('PATCH')).toEqual({ matomo_enabled: false })
  })

  it.each([
    [
      'a bad address',
      [{ loc: ['body', 'matomo_url'], type: 'matomo_url_invalid', msg: '' }],
      /Adresse de Matomo/,
      'L’adresse doit commencer par https:// et ne contenir ni ?, ni #, ni identifiant. http:// ne marche que pour localhost.'
    ],
    [
      'a bad site id',
      [{ loc: ['body', 'matomo_site_id'], type: 'matomo_site_id_invalid', msg: '' }],
      /Identifiant du site/,
      'L’identifiant du site ne contient que des chiffres.'
    ],
    [
      'a missing site id',
      'matomo_needs_url_and_site_id',
      /Identifiant du site/,
      'Renseignez l’adresse et l’identifiant du site pour activer la mesure d’audience.'
    ]
  ])('shows why the backend refused %s', async (_case, detail, field, message) => {
    mocks.request.mockRejectedValue(
      Object.assign(new Error('Error in form'), { status: 422, detail })
    )
    const { getByRole, getByLabelText } = renderPage()

    await fireEvent.click(getByRole('radio', { name: 'Activée, avec mon Matomo' }))
    await fireEvent.input(getByLabelText(/Adresse de Matomo/), {
      target: { value: 'https://stats.example.org' }
    })
    await fireEvent.click(getByRole('button', { name: 'Activer la mesure d’audience' }))

    await waitFor(() => expect(getByLabelText(field)).toHaveAccessibleDescription(message))
  })

  it.each([
    ['off', null, 'Désactivée', { matomo_enabled: false }],
    ['back to the server setting', false, /^Réglage du serveur/, { matomo_enabled: null }]
  ])('switches audience measurement %s', async (_case, matomoEnabled, choice, body) => {
    const { getByRole } = renderPage(false, matomoEnabled)
    const radio = getByRole('radio', { name: choice })

    await fireEvent.click(radio)

    await waitFor(() => expect(mocks.toast).toHaveBeenCalled())
    expect(bodyOf('PATCH')).toEqual(body)
    expect(radio).toBeChecked()
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

  it.each([
    ['off', false, serverMatomo],
    ['left to a server with no Matomo', null, noServerMatomo]
  ])('greys out the banner switch when measurement is %s', (_case, matomoEnabled, server) => {
    const { getByRole } = renderPage(true, matomoEnabled, ownMatomo, server)
    const toggle = getByRole('checkbox', { name: /Afficher le bandeau cookies/ })

    expect(toggle).toBeDisabled()
    expect(toggle).toBeChecked()
    expect(toggle).toHaveAccessibleDescription(
      'Aucune mesure d’audience, donc aucune question à poser.'
    )
  })

  it.each([
    ['on', true, noServerMatomo],
    ['left to a server with Matomo', null, serverMatomo]
  ])('lets the banner switch move when measurement is %s', (_case, matomoEnabled, server) => {
    const { getByRole } = renderPage(false, matomoEnabled, ownMatomo, server)

    expect(getByRole('checkbox', { name: /Afficher le bandeau cookies/ })).toBeEnabled()
  })

  it('greys out the banner switch once measurement is saved off', async () => {
    const { getByRole } = renderPage()
    const toggle = getByRole('checkbox', { name: /Afficher le bandeau cookies/ })

    await fireEvent.click(getByRole('radio', { name: 'Désactivée' }))

    await waitFor(() => expect(toggle).toBeDisabled())
  })

  it('keeps the banner switch as saved until On is saved', async () => {
    const { getByRole, getByLabelText } = renderPage(false, false, ownMatomo, noServerMatomo)
    const toggle = getByRole('checkbox', { name: /Afficher le bandeau cookies/ })

    await fireEvent.click(getByRole('radio', { name: 'Activée, avec mon Matomo' }))
    expect(toggle).toBeDisabled()

    mocks.request.mockResolvedValueOnce({ matomo_enabled: true, ...ownMatomo })
    await fireEvent.input(getByLabelText(/Identifiant du site/), { target: { value: '12' } })
    await fireEvent.click(getByRole('button', { name: 'Activer la mesure d’audience' }))

    await waitFor(() => expect(toggle).toBeEnabled())
  })

  it('previews the banner with its text and its two buttons', async () => {
    const { getByLabelText, getByTestId } = renderPage()

    await fireEvent.input(getByLabelText('Titre du bandeau'), {
      target: { value: 'Vos cookies' }
    })

    const preview = getByTestId('cookie-banner-preview')
    await waitFor(() => expect(preview).toHaveTextContent('Vos cookies'))
    expect(preview).toHaveTextContent(frBanner.description)
    for (const name of ['Refuser', 'Accepter']) {
      expect(within(preview).getByRole('button', { name })).toBeInTheDocument()
    }
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
