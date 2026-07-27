import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import CategoryManager from './CategoryManager.svelte'
import type { SuggestionCategory } from './types'

const { request } = vi.hoisted(() => ({ request: vi.fn() }))

vi.mock('$lib/fastapi-client', () => ({
  api: { request }
}))

vi.mock('$lib/helpers/useToast.svelte', () => ({
  useToast: vi.fn()
}))

const category = (
  title: string,
  suggestionCount: number,
  id = crypto.randomUUID()
): SuggestionCategory => ({
  id,
  locale: 'fr',
  key: title.toLowerCase(),
  title,
  description: `${title} description`,
  icon: 'i-ri-lightbulb-line',
  tooltip: null,
  display_order: 0,
  suggestion_count: suggestionCount
})

describe('CategoryManager', () => {
  beforeEach(() => {
    request.mockReset()
  })

  it('only enables deletion for an empty category', () => {
    const { getByRole, getByText } = render(CategoryManager, {
      categories: [category('Vide', 0), category('Utilisée', 3)],
      onDeleted: vi.fn()
    })

    const emptyDeleteButton = getByText('Vide').closest('li')?.querySelector('button')
    const usedDeleteButton = getByText('Utilisée').closest('li')?.querySelector('button')
    expect(emptyDeleteButton).not.toHaveAttribute('aria-disabled', 'true')
    expect(usedDeleteButton).toHaveAttribute('aria-disabled', 'true')
    expect(usedDeleteButton).toHaveAccessibleDescription('3 suggestions — suppression impossible')
    expect(getByRole('tooltip')).toHaveTextContent('3 suggestions — suppression impossible')
  })

  it('asks for confirmation before deleting an empty category', async () => {
    const onDeleted = vi.fn()
    const emptyCategory = category('Temporaire', 0, '00000000-0000-0000-0000-000000000010')
    request.mockResolvedValue(undefined)
    const { getAllByRole, getByRole } = render(CategoryManager, {
      categories: [emptyCategory],
      onDeleted
    })

    await fireEvent.click(getAllByRole('button', { name: 'Supprimer', hidden: true })[0])
    expect(getByRole('heading', { name: 'Supprimer « Temporaire » ?', hidden: true })).toBeTruthy()

    await fireEvent.click(getByRole('button', { name: 'Supprimer la catégorie', hidden: true }))

    await waitFor(() => {
      expect(request).toHaveBeenCalledWith(`/admin/suggestions/categories/${emptyCategory.id}`, {
        method: 'DELETE'
      })
      expect(onDeleted).toHaveBeenCalledOnce()
    })
  })
})
