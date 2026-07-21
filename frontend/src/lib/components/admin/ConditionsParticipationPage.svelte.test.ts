import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Page from '../../../routes/(admin)/admin/conditions-participation/+page.svelte'

const presentation = {
  arena: {
    title: 'Avant de commencer',
    introduction: 'Introduction de test',
    checkbox_label: 'J’accepte les conditions.',
    links: [{ label: 'Conditions', href: '/arene/modalites' }],
    button_label: 'Continuer'
  },
  sign_in: {
    checkbox_label: 'J’accepte avant de recevoir le code.',
    links: [{ label: 'Conditions', href: '/arene/modalites' }]
  }
}

const mocks = vi.hoisted(() => ({ request: vi.fn(), toast: vi.fn() }))

vi.mock('$lib/fastapi-client', () => ({
  api: { request: mocks.request }
}))

vi.mock('$lib/helpers/useToast.svelte', () => ({
  useToast: mocks.toast
}))

describe('Participation journey administration page', () => {
  beforeEach(() => {
    mocks.request.mockReset()
    mocks.toast.mockReset()
    mocks.request.mockImplementation((path: string, options?: RequestInit) => {
      if (path === '/admin/legal/presentation' && options?.method === 'PUT') {
        return Promise.resolve(presentation)
      }
      if (path === '/admin/legal/presentation') return Promise.resolve(presentation)
      return Promise.reject(new Error(`Unexpected request: ${path}`))
    })
  })

  it('opens directly on the editable journey without versions or history', async () => {
    const { container, getByRole, queryByText } = render(Page)

    await waitFor(() => expect(getByRole('heading', { name: 'Modifier le parcours' })).toBeTruthy())
    expect((getByRole('textbox', { name: /Titre de la fenêtre/ }) as HTMLInputElement).value).toBe(
      'Avant de commencer'
    )
    expect(queryByText(/Historique/)).toBeNull()
    expect(queryByText(/version 1\.0/i)).toBeNull()
    expect(queryByText(/Sélectionnez du texte puis utilisez/)).toBeNull()
    expect(queryByText(/saisissez directement du Markdown/)).toBeNull()
    expect(container.querySelector('.fr-hint-text')).toBeNull()
    expect(container.querySelector('.border-t')).toBeNull()
  })

  it('saves the mutable journey without publishing terms', async () => {
    const { getByRole } = render(Page)
    await waitFor(() => expect(getByRole('heading', { name: 'Modifier le parcours' })).toBeTruthy())

    await fireEvent.input(getByRole('textbox', { name: /Titre de la fenêtre/ }), {
      target: { value: 'Nouveau titre' }
    })
    await fireEvent.click(getByRole('button', { name: 'Enregistrer le parcours' }))

    await waitFor(() =>
      expect(mocks.request).toHaveBeenCalledWith(
        '/admin/legal/presentation',
        expect.objectContaining({ method: 'PUT' })
      )
    )
    const saveCall = mocks.request.mock.calls.find(
      ([path, options]) => path === '/admin/legal/presentation' && options?.method === 'PUT'
    )
    const body = JSON.parse(saveCall?.[1]?.body as string)
    expect(body.presentation.arena.title).toBe('Nouveau titre')
    expect(body.presentation.arena.links).toHaveLength(2)
  })
})
