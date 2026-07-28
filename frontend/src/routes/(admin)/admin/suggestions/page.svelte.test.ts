import { render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
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

vi.mock('$lib/fastapi-client', () => ({
  api: { request: vi.fn() }
}))

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
  it('matches the server limits on the category fields and exposes them as field descriptions', () => {
    // The page only reads filters and suggestions, so the rest of the layout
    // data the route type demands is not worth building here.
    const { getByLabelText, container } = render(Page, {
      data: { filters, suggestions } as unknown as PageProps['data'],
      params: {} as PageProps['params']
    })

    const title = getByLabelText(/Nom de la catégorie/)
    const description = getByLabelText(/^Description/)
    const tooltip = getByLabelText(/Information complémentaire/)

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
})
