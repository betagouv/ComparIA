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
          period: '30d',
          granularity: 'day',
          prompts_count: 12345,
          conversations_count: 6789,
          models_count: 31,
          preferences: { a_better: 4, b_better: 3, both_good: 2, both_bad: 1 },
          activity: [],
          preference_activity: []
        }
      } as never
    })

    expect(getByRole('heading', { level: 1, name: 'Statistiques de la plateforme' })).toBeTruthy()
    expect(getByRole('heading', { level: 3, name: 'Activité de la plateforme' })).toBeTruthy()
    expect(
      [...container.querySelectorAll('.metric-value')].map((item) => item.textContent?.trim())
    ).toEqual(['754', '527', '31'])
  })
})
