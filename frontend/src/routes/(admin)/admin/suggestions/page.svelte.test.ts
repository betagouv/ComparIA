import { fireEvent, render } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Page from './+page.svelte'
import type { PageProps } from './$types'
import type { SuggestionFilters, SuggestionsPage } from './types'

vi.mock('$app/navigation', () => ({
  goto: vi.fn(),
  invalidate: vi.fn()
}))

vi.mock('$app/paths', () => ({
  resolve: (path: string) => path
}))

vi.mock('$app/state', () => ({
  page: { url: new URL('http://localhost/admin/suggestions') }
}))

const { request } = vi.hoisted(() => ({ request: vi.fn() }))

vi.mock('$lib/fastapi-client', () => ({ api: { request } }))

vi.mock('$lib/helpers/useToast.svelte', () => ({
  useToast: vi.fn()
}))

const filters: SuggestionFilters = { search: '', status: '', locale: '', category_id: '' }
const suggestions: SuggestionsPage = {
  items: [],
  total: 0,
  page: 1,
  page_size: 25,
  categories: []
}

describe('admin suggestions page', () => {
  beforeEach(() => {
    request.mockReset()
    Object.assign(window, {
      dsfr: () => ({ modal: { disclose: vi.fn(), conceal: vi.fn() } })
    })
  })

  it('matches the server limits on the category fields and exposes them as field descriptions', () => {
    // The page only reads filters and suggestions, so the rest of the layout
    // data the route type demands is not worth building here.
    const { getByLabelText, getAllByText, queryByRole, container } = render(Page, {
      data: { filters, suggestions } as unknown as PageProps['data'],
      params: {} as PageProps['params']
    })

    const title = getByLabelText(/Nom de la catégorie/)
    const description = getByLabelText(/^Description/)
    const tooltip = getByLabelText(/Information complémentaire/)

    expect(
      getAllByText('Recherche').find((element) => element.hasAttribute('aria-hidden'))
    ).toBeTruthy()
    expect(queryByRole('navigation', { name: 'Pagination' })).toBeNull()

    const accessibleDescription = (element: HTMLElement) =>
      element
        .getAttribute('aria-describedby')
        ?.split(' ')
        .map((id) => container.querySelector(`#${id}`)?.textContent?.trim())
        .filter(Boolean)
        .join(' ')

    expect(title.getAttribute('maxlength')).toBe('100')
    expect(accessibleDescription(title)).toBe('100 caractères maximum')
    expect(description.getAttribute('maxlength')).toBe('300')
    expect(accessibleDescription(description)).toBe(
      'Cette description est affichée sous le nom de la catégorie dans l’arène. 300 caractères maximum'
    )
    expect(tooltip.getAttribute('maxlength')).toBe('300')
    expect(accessibleDescription(tooltip)).toBe(
      'Facultatif. Cette information sera accessible depuis une infobulle. 300 caractères maximum'
    )
  })

  it('groups suggestions under category headings and archives a whole category', async () => {
    request.mockResolvedValue(undefined)
    const categoryId = '00000000-0000-0000-0000-000000000010'
    const archivedCategoryId = '00000000-0000-0000-0000-000000000012'
    const groupedSuggestions: SuggestionsPage = {
      items: [
        {
          id: '00000000-0000-0000-0000-000000000011',
          text: 'Explique-moi le fonctionnement du Sénat',
          locale: 'fr',
          category_id: categoryId,
          category_title: 'Comprendre les institutions',
          status: 'available',
          created_at: '2026-08-18T10:00:00',
          updated_at: '2026-08-18T10:00:00'
        },
        {
          id: '00000000-0000-0000-0000-000000000013',
          text: 'Une ancienne suggestion',
          locale: 'fr',
          category_id: archivedCategoryId,
          category_title: 'Archives',
          status: 'archived',
          created_at: '2026-08-18T09:00:00',
          updated_at: '2026-08-18T09:00:00'
        }
      ],
      total: 2,
      page: 1,
      page_size: 25,
      categories: [
        {
          id: categoryId,
          locale: 'fr',
          key: 'institutions',
          title: 'Comprendre les institutions',
          description: 'Questions sur la vie publique',
          icon: 'i-ri-book-open-line',
          tooltip: null,
          display_order: 0,
          suggestion_count: 1,
          available_suggestion_count: 1
        },
        {
          id: archivedCategoryId,
          locale: 'fr',
          key: 'archives',
          title: 'Archives',
          description: 'Anciennes suggestions',
          icon: 'i-ri-archive-line',
          tooltip: null,
          display_order: 0,
          suggestion_count: 1,
          available_suggestion_count: 0
        }
      ]
    }
    const { getByRole, getByText, queryByText, container } = render(Page, {
      data: { filters, suggestions: groupedSuggestions } as unknown as PageProps['data'],
      params: {} as PageProps['params']
    })

    expect(getByRole('heading', { name: 'Comprendre les institutions' })).toBeTruthy()
    expect(getByText('Explique-moi le fonctionnement du Sénat')).toBeTruthy()
    expect(
      [...container.querySelectorAll('section h2')].map((heading) => heading.textContent?.trim())
    ).toEqual(['Comprendre les institutions', 'Archives'])

    await fireEvent.click(
      getByRole('button', { name: 'Replier la catégorie: Comprendre les institutions' })
    )
    expect(queryByText('Explique-moi le fonctionnement du Sénat')).toBeNull()
    await fireEvent.click(
      getByRole('button', { name: 'Déplier la catégorie: Comprendre les institutions' })
    )

    await fireEvent.click(
      getByRole('button', {
        name: 'Archiver la catégorie: Comprendre les institutions'
      })
    )
    await fireEvent.click(getByRole('button', { name: 'Archiver la catégorie', hidden: true }))

    expect(request).toHaveBeenCalledWith(`/admin/suggestions/categories/${categoryId}`, {
      method: 'PATCH',
      body: JSON.stringify({ archived: true })
    })
  })
})
