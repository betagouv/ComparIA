import { render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import Page from './+page.svelte'
import ConversationActivityChart from './ConversationActivityChart.svelte'

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
          range_start: '2025-12-03',
          range_end: '2026-01-01',
          prompts_count: 12345,
          conversations_count: 6789,
          votes_count: 4321,
          models_count: 31,
          activity: [{ date: '2026-01-01', prompts: 42, conversations: 21 }]
        }
      } as never
    })

    expect(getByRole('heading', { level: 1, name: 'Statistiques de la plateforme' })).toBeTruthy()
    expect(getByRole('heading', { level: 3, name: 'Activité de la plateforme' })).toBeTruthy()
    expect(
      [...container.querySelectorAll('.metric-value')].map((item) => item.textContent?.trim())
    ).toEqual([12345, 6789, 4321, 31].map((value) => new Intl.NumberFormat('fr').format(value)))
  })

  it('clips weekly labels to the selected period boundaries', () => {
    const { container } = render(ConversationActivityChart, {
      points: [
        { date: '2026-05-04', prompts: 2, conversations: 1 },
        { date: '2026-08-03', prompts: 3, conversations: 2 }
      ],
      granularity: 'week',
      rangeStart: '2026-05-08',
      rangeEnd: '2026-08-05',
      title: 'Activity',
      labels: {
        table: 'View table',
        date: 'Date',
        prompts: 'Prompts',
        conversations: 'Conversations'
      }
    })
    const formatter = new Intl.DateTimeFormat('fr', { day: 'numeric', month: 'short' })
    const expectedFirstRange = formatter.formatRange(
      new Date('2026-05-08T12:00:00'),
      new Date('2026-05-10T12:00:00')
    )
    const expectedLastRange = formatter.formatRange(
      new Date('2026-08-03T12:00:00'),
      new Date('2026-08-05T12:00:00')
    )

    expect(container.textContent).toContain(expectedFirstRange)
    expect(container.textContent).toContain(expectedLastRange)
  })
})
