import { api } from '$lib/fastapi-client'
import type { AdminLimits, LimitsCalibration } from '$lib/generated/admin'
import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { PageProps } from './$types'
import Page from './+page.svelte'

vi.mock('$app/navigation', () => ({ invalidate: vi.fn() }))
vi.mock('$lib/fastapi-client', () => ({ api: { request: vi.fn() } }))
vi.mock('$lib/helpers/useToast.svelte', () => ({ useToast: vi.fn() }))

const limit = (name: string, value: number, stored = false) => ({
  name,
  value,
  default: value,
  stored
})

const limits = {
  limits: [
    { ...limit('all_per_session', 5_000, true), default: 3_000_000 },
    limit('all_per_ip', 60_000_000),
    limit('expensive_per_session', 0.4),
    limit('expensive_per_ip', 20),
    limit('expensive_price_out', 8),
    limit('expected_answer_chars', 508),
    limit('in_flight_per_network', 40)
  ],
  llms: [{ id: 'gpt', name: 'GPT 5.5', price_in: 4.3, price_out: 26 }],
  updated_at: null,
  updated_by: null,
  calibration_days: 7
} as unknown as AdminLimits

const usage = [
  {
    llm_id: 'gpt',
    name: 'GPT 5.5',
    input_chars: 0,
    output_chars: 0,
    estimated_usd: 0.52,
    cap_usd: null,
    resting: false,
    resets_in: 3600,
    answers: 4,
    cached_answers: 0
  }
]

const calibration = {
  days: 7,
  comparisons: 100,
  turns: 300,
  capped: false,
  proposals: [{ name: 'expected_answer_chars', value: 600, sample: 200, percentile: 50 }],
  daily_caps: [{ llm_id: 'gpt', value: 3, days: 6, percentile: 95, highest: 2 }],
  price_checks: []
} as unknown as LimitsCalibration

const request = vi.mocked(api.request)

beforeEach(() => request.mockReset())

function page() {
  return render(Page, { data: { limits, usage } } as unknown as PageProps)
}

describe('limits page', () => {
  it("puts one value back on its default and keeps the admin's other edits and proposals", async () => {
    request.mockImplementation(async (url: string) =>
      url === '/admin/limits/calibration' ? calibration : limits
    )
    const view = page()
    await fireEvent.click(view.getByRole('button', { name: 'Calibrer' }))
    await waitFor(() => expect(view.getByText(/Plafond proposé/)).toBeInTheDocument())
    const network = view.container.querySelector<HTMLInputElement>('#limit-all_per_ip')!
    await fireEvent.input(network, { target: { value: '50000000' } })

    await fireEvent.click(view.getByRole('button', { name: /Revenir au défaut/ }))

    await waitFor(() =>
      expect(request).toHaveBeenLastCalledWith('/admin/limits', {
        method: 'PATCH',
        body: JSON.stringify({ all_per_session: null })
      })
    )
    expect(network).toHaveValue(50_000_000)
    expect(view.container.querySelector('#limit-expected_answer_chars')).toHaveValue(600)
    expect(view.container.querySelector('#limit-all_per_session')).toHaveValue(3_000_000)
    expect(view.getByText(/Plafond proposé/)).toBeInTheDocument()
  })
})
