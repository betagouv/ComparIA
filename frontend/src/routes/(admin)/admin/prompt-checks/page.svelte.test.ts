import type { PromptCheckStatus } from '$lib/generated/admin'
import { render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import type { PageProps } from './$types'
import Page from './+page.svelte'
import type { PromptCheckStats, PromptCheckTry } from './types'

vi.mock('$app/navigation', () => ({
  invalidate: vi.fn()
}))

vi.mock('$lib/fastapi-client', () => ({
  api: { request: vi.fn() }
}))

vi.mock('$lib/helpers/useToast.svelte', () => ({
  useToast: vi.fn()
}))

const categories = {
  sexual: { threshold: 0.3, action: 'log' },
  selfharm: { threshold: 0.3, action: 'log' },
  hate_and_discrimination: { threshold: 0.5, action: 'log' },
  violence_and_threats: { threshold: 0.5, action: 'log' },
  dangerous: { threshold: 0.5, action: 'log' },
  criminal: { threshold: 0.5, action: 'log' },
  jailbreaking: { threshold: 0.5, action: 'log' },
  pii: { threshold: 0.5, action: 'warn' },
  health: { threshold: 0.5, action: 'off' },
  law: { threshold: 0.5, action: 'off' },
  financial: { threshold: 0.5, action: 'off' }
}

const check = (overrides: Partial<PromptCheckStatus> = {}): PromptCheckStatus =>
  ({
    model: 'mistral-moderation-latest',
    categories: { ...categories },
    updated_at: '2026-07-01T10:00:00',
    consecutive_failures: 0,
    healthy: true,
    warnings_shown: 0,
    ...overrides
  }) as unknown as PromptCheckStatus

const tried = (overrides: Partial<PromptCheckTry> = {}): PromptCheckTry => ({
  decision: 'warned',
  scores: {
    sexual: 0.01,
    selfharm: 0.0,
    hate_and_discrimination: 0.02,
    violence_and_threats: 0.0,
    dangerous: 0.0,
    criminal: 0.41,
    jailbreaking: 0.03,
    pii: 0.99,
    health: 0.7,
    law: 0.0,
    financial: 0.0
  },
  triggered: { pii: 'warn' },
  message: 'Votre message semble contenir des données personnelles.',
  latency_ms: 210,
  ...overrides
})

const stats = (overrides: Partial<PromptCheckStats> = {}): PromptCheckStats => ({
  days: 30,
  total: 1234,
  by_decision: { pass: 1000, logged: 200, warned: 30, blocked: 4, error: 0 },
  by_category: { pii: 22, criminal: 8 },
  proceeded: 21,
  warnings_shown: 30,
  ...overrides
})

const renderPage = (status: PromptCheckStatus, pageStats: PromptCheckStats | null = null) =>
  render(Page, {
    data: {
      check: status,
      stats: pageStats,
      statsDays: 30
    } as unknown as PageProps['data'],
    params: {} as PageProps['params']
  })

const runBench = async (container: HTMLElement, text: string) => {
  const field = container.querySelector<HTMLTextAreaElement>('#prompt-check-bench-text')!
  field.value = text
  field.dispatchEvent(new Event('input', { bubbles: true }))
  container.querySelector<HTMLButtonElement>('#prompt-check-bench-run')!.click()
  await Promise.resolve()
  await Promise.resolve()
}

describe('admin prompt check page', () => {
  it('saves a threshold the number input handed back as a number', async () => {
    const { api } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockResolvedValue(check())

    const { container } = renderPage(check())
    const field = container.querySelector<HTMLInputElement>('#prompt-check-threshold-pii')!
    field.value = '0.65'
    field.dispatchEvent(new Event('input', { bubbles: true }))
    container.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true }))
    await Promise.resolve()

    expect(api.request).toHaveBeenCalledWith(
      '/admin/prompt-check',
      expect.objectContaining({ method: 'PATCH' })
    )
    const body = JSON.parse(vi.mocked(api.request).mock.calls[0][1]!.body as string)
    expect(body.categories.pii).toEqual({ threshold: 0.65, action: 'warn' })
    expect(Object.keys(body.categories).length).toBe(11)
    expect(body.model).toBe('mistral-moderation-latest')
  })

  it('offers the four actions per category and preselects the stored one', () => {
    const { container } = renderPage(check())

    const labels = [...container.querySelectorAll('#prompt-check-row-sexual .action-pills label')]
      .map((label) => label.textContent?.trim())
      .filter(Boolean)
    expect(labels).toEqual(['Ignorer', 'Surveiller', 'Prévenir', 'Refuser'])

    const checked = (id: string) =>
      container.querySelector<HTMLInputElement>(`#prompt-check-action-${id}`)?.checked
    expect(checked('sexual-log')).toBe(true)
    expect(checked('sexual-block')).toBe(false)
    expect(checked('pii-warn')).toBe(true)
  })

  it('bounds every threshold field between 0 and 1', () => {
    renderPage(check())

    const field = document.querySelector<HTMLInputElement>('#prompt-check-threshold-sexual')
    expect(field?.value).toBe('0.3')
    expect(field?.getAttribute('min')).toBe('0')
    expect(field?.getAttribute('max')).toBe('1')
  })

  it('refuses a threshold outside 0 and 1 rather than sending it', async () => {
    const { api } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockClear()

    const { container, getByText } = renderPage(check())
    const field = container.querySelector<HTMLInputElement>('#prompt-check-threshold-sexual')!
    field.value = '1.4'
    field.dispatchEvent(new Event('input', { bubbles: true }))
    container.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true }))
    await Promise.resolve()

    expect(api.request).not.toHaveBeenCalled()
    expect(getByText('Saisissez un nombre entre 0 et 1.')).toBeInTheDocument()
  })

  it('lets the product categories be configured, seeded off rather than locked', () => {
    const { getAllByText } = renderPage(check())

    for (const label of ['Santé', 'Droit', 'Finance']) {
      expect(getAllByText(label).length).toBeGreaterThan(0)
    }
    const off = document.querySelector<HTMLInputElement>('#prompt-check-action-health-off')
    expect(off).toBeInTheDocument()
    expect(off?.checked).toBe(true)
    expect(off?.disabled).toBe(false)
    expect(
      document.querySelector('#prompt-check-action-health-block')?.hasAttribute('disabled')
    ).toBe(false)
    expect(document.querySelector('#prompt-check-threshold-health')).toBeInTheDocument()
  })

  it('explains what the four actions do, warning included', () => {
    const { getByText } = renderPage(check())

    expect(getByText('Ce que fait chaque action')).toBeInTheDocument()
    expect(getByText(/La personne peut envoyer quand même/)).toBeInTheDocument()
  })

  it('says so when the check has stopped working, and stays quiet when it has not', () => {
    const { getByText, queryByText, unmount } = renderPage(
      check({ healthy: false, consecutive_failures: 7 })
    )

    expect(getByText('La vérification ne répond plus')).toBeInTheDocument()
    expect(getByText('7 échecs consécutifs')).toBeInTheDocument()
    unmount()

    const healthy = renderPage(check())
    expect(healthy.queryByText('La vérification ne répond plus')).not.toBeInTheDocument()
    expect(queryByText('0 échecs consécutifs')).not.toBeInTheDocument()
  })

  it('runs the bench against the on-screen rules, not the stored ones', async () => {
    const { api } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockReset()
    vi.mocked(api.request).mockResolvedValue(tried())

    const { container } = renderPage(check())
    const threshold = container.querySelector<HTMLInputElement>('#prompt-check-threshold-pii')!
    threshold.value = '0.65'
    threshold.dispatchEvent(new Event('input', { bubbles: true }))
    const action = container.querySelector<HTMLInputElement>('#prompt-check-action-sexual-block')!
    action.checked = true
    action.dispatchEvent(new Event('change', { bubbles: true }))

    await runBench(container, 'un message à vérifier')

    expect(api.request).toHaveBeenCalledWith(
      '/admin/prompt-check/try',
      expect.objectContaining({ method: 'POST' })
    )
    const body = JSON.parse(vi.mocked(api.request).mock.calls[0][1]!.body as string)
    expect(body.text).toBe('un message à vérifier')
    expect(body.model).toBe('mistral-moderation-latest')
    expect(body.categories.pii).toEqual({ threshold: 0.65, action: 'warn' })
    expect(body.categories.sexual).toEqual({ threshold: 0.3, action: 'block' })
    expect(Object.keys(body.categories).length).toBe(11)
  })

  it('shows every category score, whether it fired or not', async () => {
    const { api } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockReset()
    vi.mocked(api.request).mockResolvedValue(tried())

    const { container, getByText } = renderPage(check())
    await runBench(container, 'appelle Jean Dupont au 06 12 34 56 78')

    expect(getByText('Prévenu')).toBeInTheDocument()
    expect(getByText('Réponse en 210 ms')).toBeInTheDocument()
    expect(container.querySelector('#prompt-check-bench-message')?.textContent?.trim()).toBe(
      'Votre message semble contenir des données personnelles.'
    )

    const fired = container.querySelector('#prompt-check-bench-row-pii')!
    expect(fired.textContent).toContain('0,990')
    expect(fired.textContent).toContain('0,500')
    expect(fired.textContent).toContain('Déclenchée')

    // La quasi-atteinte : 0,410 contre un seuil de 0,300 dans le sens inverse,
    // et surtout une catégorie qui n'a pas tiré reste visible avec sa note.
    const quiet = container.querySelector('#prompt-check-bench-row-criminal')!
    expect(quiet.textContent).toContain('0,410')
    expect(quiet.textContent).toContain('0,500')
    expect(quiet.textContent).toContain('Sous le seuil')
  })

  it('renders the counts for the window', () => {
    const { container, getByText } = renderPage(check(), stats())

    expect(container.querySelector('#prompt-check-stats-total')?.textContent?.trim()).toBe('1234')
    expect(getByText('Activité des 30 derniers jours')).toBeInTheDocument()

    const blocked = container.querySelector('#prompt-check-stats-decision-blocked')?.textContent
    expect(blocked).toContain('Refusés')
    expect(blocked).toContain('4')

    const passed = container.querySelector('#prompt-check-stats-decision-pass')?.textContent
    expect(passed).toContain('Passés sans rien')
    expect(passed).toContain('1000')

    const pii = container.querySelector('#prompt-check-stats-category-pii')?.textContent
    expect(pii).toContain('Données personnelles')
    expect(pii).toContain('22')
    const warnings = container.querySelector('#prompt-check-stats-warnings')?.textContent
    expect(warnings).toContain('30 affichés')
    expect(warnings).toContain('21 envoyés quand même')
  })

  it('stays readable when the counts are missing', () => {
    const { getByText } = renderPage(check())

    expect(getByText('Les compteurs ne sont pas disponibles pour le moment.')).toBeInTheDocument()
  })
})
