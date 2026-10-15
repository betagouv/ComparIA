import { api } from '$lib/fastapi-client'
import type { AdminLimits, LimitsCalibration } from '$lib/generated/admin'
import { fireEvent, render, waitFor, within } from '@testing-library/svelte'
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
    full: false,
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
const modal = { disclose: vi.fn(), conceal: vi.fn() }

beforeEach(() => {
  request.mockReset()
  modal.disclose.mockClear()
  Object.defineProperty(window, 'dsfr', { configurable: true, value: () => ({ modal }) })
})

/** The confirmation dialog, which DSFR shows on `disclose`. */
function dialog(view: ReturnType<typeof page>) {
  return within(view.container.querySelector<HTMLElement>('#limits-confirm')!)
}

// "Appliquer", then the same button in the dialog that lists the changes.
async function apply(view: ReturnType<typeof page>) {
  const form = view.container.querySelector('form')!
  await fireEvent.click(within(form).getByRole('button', { name: /^Appliquer/ }))
  expect(modal.disclose).toHaveBeenCalledOnce()
  await fireEvent.click(dialog(view).getByRole('button', { name: /^Appliquer/, hidden: true }))
}

function page() {
  return render(Page, { data: { limits, usage } } as unknown as PageProps)
}

describe('limits page', () => {
  it('puts a value back on its default only once applied, with the other edits', async () => {
    request.mockImplementation(async (url: string) =>
      url === '/admin/limits/calibration' ? calibration : limits
    )
    const view = page()
    await fireEvent.click(view.getByRole('button', { name: 'Calibrer' }))
    await waitFor(() => expect(view.getByText(/Plafond proposé/)).toBeInTheDocument())
    const network = view.container.querySelector<HTMLInputElement>('#limit-all_per_ip')!
    await fireEvent.input(network, { target: { value: '50000000' } })

    await fireEvent.click(view.getByRole('button', { name: /Revenir au défaut/ }))

    // Nothing is stored yet: the field holds the default, like any edit.
    expect(request).not.toHaveBeenCalledWith('/admin/limits', expect.anything())
    expect(view.container.querySelector('#limit-all_per_session')).toHaveValue(3_000_000)
    expect(network).toHaveValue(50_000_000)
    expect(view.container.querySelector('#limit-expected_answer_chars')).toHaveValue(600)

    await apply(view)

    await waitFor(() =>
      expect(request).toHaveBeenLastCalledWith('/admin/limits', {
        method: 'PATCH',
        body: JSON.stringify({
          all_per_session: null,
          all_per_ip: 50_000_000,
          expected_answer_chars: 600,
          daily_usd_caps: { gpt: 3 }
        })
      })
    )
  })

  it('says when a proposal was read from too few windows to trust', async () => {
    const small = {
      ...calibration,
      comparisons: 1,
      turns: 1,
      proposals: [
        { name: 'all_per_session', value: 4000, sample: 1, percentile: 99, few: true },
        { name: 'expected_answer_chars', value: 600, sample: 200, percentile: 50, few: false }
      ]
    }
    request.mockImplementation(async (url: string) =>
      url === '/admin/limits/calibration' ? small : limits
    )
    const view = page()

    await fireEvent.click(view.getByRole('button', { name: 'Calibrer' }))

    await waitFor(() =>
      expect(view.getByText(/périodes de deux heures lues : 1\)/)).toBeInTheDocument()
    )
    expect(view.getAllByText(/Trop peu de données pour s'y fier/)).toHaveLength(1)
    expect(view.getByText(/Conversations lues : 1 ; messages : 1/)).toBeInTheDocument()
    expect(view.queryByText(/1 périodes|1 conversations/)).toBeNull()
  })

  it('spells out each typed value, and says it in messages once calibrated', async () => {
    request.mockImplementation(async (url: string) =>
      url === '/admin/limits/calibration'
        ? { ...calibration, message_chars: 1_000, message_usd: 0.02 }
        : limits
    )
    const view = page()
    const person = view.container.querySelector<HTMLInputElement>('#limit-all_per_session')!
    expect(person).toHaveAccessibleDescription(/^5\s000 caractères/)
    await fireEvent.input(person, { target: { value: '31000' } })
    expect(person).toHaveAccessibleDescription(/^31\s000 caractères/)
    expect(view.queryByText(/Soit environ/)).toBeNull()

    await fireEvent.click(view.getByRole('button', { name: 'Calibrer' }))

    await waitFor(() =>
      expect(
        view.getByText('Soit environ 5 messages en deux heures pour une personne.')
      ).toBeInTheDocument()
    )
    // 20 $ for a network, at 0,02 $ a message.
    expect(
      view.getByText(/^Soit environ 1\s000 messages en deux heures pour tout le réseau\.$/)
    ).toBeInTheDocument()
    expect(view.getByRole('heading', { name: 'Réglages techniques', level: 2 })).toBeInTheDocument()
  })

  it('shows each change as old → new, and flags one past three times', async () => {
    const view = page()
    const card = (id: string) => view.container.querySelector(`#${id}`)!.closest('.cg-border')!
    expect(view.queryByText(/→/)).toBeNull()

    await fireEvent.input(view.container.querySelector('#limit-all_per_ip')!, {
      target: { value: '600000' }
    })
    await fireEvent.input(view.container.querySelector('#limit-expensive_per_ip')!, {
      target: { value: '24' }
    })

    expect(card('limit-all_per_ip')).toHaveTextContent(
      /60\s000\s000 → 600\s000 caractères \(100 fois moins\)/
    )
    expect(card('limit-all_per_ip')).toHaveTextContent(
      "Gros changement : vérifiez avant d'appliquer."
    )
    expect(card('limit-expensive_per_ip')).toHaveTextContent(
      /20,00\s\$ → 24,00\s\$ \(1,2 fois plus\)/
    )
    expect(card('limit-expensive_per_ip')).not.toHaveTextContent('Gros changement')
  })

  it('stores nothing until the dialog listing every change is confirmed', async () => {
    request.mockImplementation(async (url: string) =>
      url === '/admin/limits/calibration' ? calibration : limits
    )
    const view = page()
    const form = within(view.container.querySelector('form')!)
    expect(form.getByRole('button', { name: 'Appliquer' })).toBeInTheDocument()
    await fireEvent.click(view.getByRole('button', { name: 'Calibrer' }))
    await waitFor(() => expect(view.getByText(/Plafond proposé/)).toBeInTheDocument())
    await fireEvent.input(view.container.querySelector('#limit-all_per_ip')!, {
      target: { value: '600000' }
    })

    // The proposed answer length, the network value and GPT 5.5's cap.
    await fireEvent.click(form.getByRole('button', { name: 'Appliquer 3 changements' }))

    expect(modal.disclose).toHaveBeenCalledOnce()
    expect(request).not.toHaveBeenCalledWith('/admin/limits', expect.anything())
    const items = dialog(view)
      .getAllByRole('listitem', { hidden: true })
      .map((item) => item.textContent?.replace(/\s+/g, ' ').trim())
    expect(items).toEqual([
      'Tous les modèles · Par réseau (école, entreprise) : 60 000 000 → 600 000 caractères (100 fois moins) Gros changement.',
      'Longueur de réponse réservée : 508 → 600 caractères (1,2 fois plus)',
      'Plafond du jour de GPT 5.5 : Aucun → 3,00 $'
    ])

    await fireEvent.click(
      dialog(view).getByRole('button', { name: 'Revoir les valeurs', hidden: true })
    )
    expect(modal.conceal).toHaveBeenCalled()
    expect(request).not.toHaveBeenCalledWith('/admin/limits', expect.anything())

    await fireEvent.click(
      dialog(view).getByRole('button', { name: 'Appliquer 3 changements', hidden: true })
    )
    await waitFor(() =>
      expect(request).toHaveBeenLastCalledWith('/admin/limits', {
        method: 'PATCH',
        body: JSON.stringify({
          all_per_ip: 600_000,
          expected_answer_chars: 600,
          daily_usd_caps: { gpt: 3 }
        })
      })
    )
  })
})
