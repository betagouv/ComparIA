import { fireEvent, render, waitFor, within } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import InformationalLegalPagesAdmin from './InformationalLegalPagesAdmin.svelte'

const mocks = vi.hoisted(() => ({ request: vi.fn(), toast: vi.fn() }))
vi.mock('$lib/fastapi-client', () => ({ api: { request: mocks.request } }))
vi.mock('$lib/helpers/useToast.svelte', () => ({ useToast: mocks.toast }))

const pages = {
  legal_notice: {
    mode: 'internal',
    external_url: null,
    visible_in_legal_menu: true,
    visible_in_settings: false,
    content_by_locale: { fr: '# Mentions légales', en: '# Legal notice' }
  },
  accessibility: {
    mode: 'external',
    external_url: 'https://example.test/accessibility',
    visible_in_legal_menu: true,
    visible_in_settings: true,
    content_by_locale: { fr: '', en: '' }
  },
  ecodesign: {
    mode: 'internal',
    external_url: null,
    visible_in_legal_menu: false,
    visible_in_settings: true,
    content_by_locale: { fr: '# Écoconception', en: '' }
  }
}

describe('informational legal pages administration', () => {
  beforeEach(() => {
    mocks.request.mockReset()
    mocks.toast.mockReset()
    mocks.request.mockImplementation((_path: string, options?: RequestInit) => {
      if (options?.method === 'PUT') return Promise.resolve({ pages })
      return Promise.resolve({ pages: structuredClone(pages) })
    })
  })

  it('shows internal content and the external URL according to the selected mode', async () => {
    const { getByRole, queryByRole } = render(InformationalLegalPagesAdmin)

    await waitFor(() =>
      expect(getByRole('group', { name: 'Mentions légales' })).toBeInTheDocument()
    )
    expect(
      within(getByRole('group', { name: 'Mentions légales' })).getByRole('textbox', {
        name: /Contenu en Français/
      })
    ).toHaveValue('# Mentions légales')
    expect(getByRole('textbox', { name: /Adresse de la page externe/ })).toHaveValue(
      'https://example.test/accessibility'
    )
    expect(queryByRole('checkbox', { name: 'Le pied de page' })).not.toBeInTheDocument()
  })

  it('saves destination, visibility and localized content together', async () => {
    const { getByRole } = render(InformationalLegalPagesAdmin)
    await waitFor(() => expect(getByRole('button', { name: 'Enregistrer les pages' })).toBeTruthy())

    await fireEvent.click(
      within(getByRole('group', { name: 'Mentions légales' })).getByRole('checkbox', {
        name: 'La page Paramètres'
      })
    )
    await fireEvent.click(getByRole('button', { name: 'Enregistrer les pages' }))

    await waitFor(() =>
      expect(mocks.request).toHaveBeenCalledWith(
        '/admin/legal/informational-pages',
        expect.objectContaining({ method: 'PUT' })
      )
    )
    const putCall = mocks.request.mock.calls.find(([, options]) => options?.method === 'PUT')
    const body = JSON.parse(putCall?.[1]?.body as string)
    expect(body.pages.legal_notice.visible_in_settings).toBe(true)
    expect(body.pages.legal_notice.content_by_locale.fr).toBe('# Mentions légales')
  })

  it('rejects an insecure external address', async () => {
    const { getByRole, getByText } = render(InformationalLegalPagesAdmin)
    const url = await waitFor(() => getByRole('textbox', { name: /Adresse de la page externe/ }))

    await fireEvent.input(url, { target: { value: 'http://example.test/accessibility' } })
    await fireEvent.click(getByRole('button', { name: 'Enregistrer les pages' }))

    expect(getByText('Saisissez une adresse HTTPS valide.')).toBeInTheDocument()
    expect(mocks.request).not.toHaveBeenCalledWith(
      '/admin/legal/informational-pages',
      expect.objectContaining({ method: 'PUT' })
    )
  })
})
