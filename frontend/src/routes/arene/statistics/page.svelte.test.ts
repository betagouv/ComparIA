import { render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import Page from './+page.svelte'

const { getLocale } = vi.hoisted(() => ({ getLocale: vi.fn(() => 'fr') }))

vi.mock('$lib/i18n/runtime', async (importOriginal) => ({
  ...(await importOriginal<object>()),
  getLocale
}))

describe('statistics page', () => {
  it('presents the headline metrics with localized formatting', () => {
    const { container, getByRole } = render(Page, {
      data: {
        statistics: {
          questions_count: 12345,
          votes_count: 6789,
          daily_conversations: []
        }
      }
    })

    expect(getByRole('heading', { level: 1, name: 'Statistiques de la plateforme' })).toBeTruthy()
    expect(getByRole('heading', { level: 3, name: 'Conversations quotidiennes' })).toBeTruthy()
    expect(
      [...container.querySelectorAll('.metric-value')].map((item) => item.textContent?.trim())
    ).toEqual(['12 345', '6 789'])
  })
})
