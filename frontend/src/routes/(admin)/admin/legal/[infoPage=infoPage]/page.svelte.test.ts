import type { InformationalPageKey } from '$lib/informational-pages.svelte'
import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { PageData } from './$types'
import Page from './+page.svelte'

const mocks = vi.hoisted(() => ({ request: vi.fn(), toast: vi.fn() }))
vi.mock('$lib/fastapi-client', () => ({ api: { request: mocks.request } }))
vi.mock('$lib/helpers/useToast.svelte', () => ({ useToast: mocks.toast }))
vi.mock('$lib/authContext.svelte', () => ({
  getAuthContext: () => ({ config: { default_locale: 'fr' } }),
  getPlatformName: () => 'Compar:IA',
  tryGetAuthContext: () => ({ config: { default_locale: 'fr' } })
}))

const pages = {
  legal_notice: {
    mode: 'internal' as const,
    external_url: null,
    visible_in_legal_menu: true,
    visible_in_settings: false,
    content_by_locale: { fr: '# Mentions légales', en: '# Legal notice' }
  },
  accessibility: {
    mode: 'external' as const,
    external_url: 'https://example.test/accessibility',
    visible_in_legal_menu: true,
    visible_in_settings: true,
    content_by_locale: { fr: '', en: '' }
  },
  ecodesign: {
    mode: 'internal' as const,
    external_url: null,
    visible_in_legal_menu: false,
    visible_in_settings: true,
    content_by_locale: { fr: '', en: '# Eco-design' }
  }
}

function renderPage(key: InformationalPageKey) {
  return render(Page, {
    data: { page: pages[key] } as unknown as PageData,
    params: { infoPage: key }
  })
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

  it('shows internal content according to the selected mode', async () => {
    const { container } = renderPage('legal_notice')

    await waitFor(() =>
      expect(container.querySelector('h2')?.textContent).toContain('Mentions légales')
    )
    expect(container.querySelector('textarea')).toHaveValue('# Mentions légales')
  })

  it('shows external URL according to the selected mode', async () => {
    const { container } = renderPage('accessibility')

    expect(container.querySelector('#external_url')).toHaveValue(
      'https://example.test/accessibility'
    )
  })

  it('saves destination, visibility and localized content together', async () => {
    const { getByRole } = renderPage('legal_notice')
    await waitFor(() => expect(getByRole('button', { name: 'Enregistrer' })).toBeTruthy())

    await fireEvent.click(getByRole('checkbox', { name: 'La page Paramètres' }))
    await fireEvent.click(getByRole('button', { name: 'Enregistrer' }))

    await waitFor(() =>
      expect(mocks.request).toHaveBeenCalledWith(
        '/admin/legal/informational-page/legal_notice',
        expect.objectContaining({ method: 'put' })
      )
    )
    const putCall = mocks.request.mock.calls.find(([, options]) => options?.method === 'put')
    const body = JSON.parse(putCall?.[1]?.body as string)
    expect(body.visible_in_settings).toBe(true)
    expect(body.content_by_locale.fr).toBe('# Mentions légales')
  })

  it('rejects a missing default locale f', async () => {
    const { getByRole, getByText } = renderPage('ecodesign')

    await fireEvent.click(getByRole('button', { name: 'Enregistrer' }))

    expect(getByText('Traduction principale manquante')).toBeInTheDocument()
    expect(mocks.request).not.toHaveBeenCalledWith('/admin/legal/informational-page')
  })
})
