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
    enabled: true,
    has_api_key: false,
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

const submit = async (container: HTMLElement, form: string) => {
  container
    .querySelector(`#prompt-check-${form}-form`)!
    .dispatchEvent(new Event('submit', { bubbles: true }))
  await Promise.resolve()
}

const type = (container: HTMLElement, selector: string, value: string) => {
  const field = container.querySelector<HTMLInputElement>(selector)!
  field.value = value
  field.dispatchEvent(new Event('input', { bubbles: true }))
  return field
}

const sentBody = async () => {
  const { api } = await import('$lib/fastapi-client')
  return JSON.parse(vi.mocked(api.request).mock.calls[0][1]!.body as string)
}

describe('admin prompt check page', () => {
  it('saves a threshold the number input handed back as a number', async () => {
    const { api } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockReset()
    vi.mocked(api.request).mockResolvedValue(check())

    const { container } = renderPage(check())
    type(container, '#prompt-check-threshold-pii', '0.65')
    await submit(container, 'categories')

    expect(api.request).toHaveBeenCalledWith(
      '/admin/prompt-check',
      expect.objectContaining({ method: 'PATCH' })
    )
    const body = await sentBody()
    expect(body.categories.pii).toEqual({ threshold: 0.65, action: 'warn' })
    expect(Object.keys(body.categories).length).toBe(11)
  })

  it('sends the categories on their own, without the model or the key', async () => {
    const { api } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockReset()
    vi.mocked(api.request).mockResolvedValue(check())

    const { container } = renderPage(check({ has_api_key: true }))
    await submit(container, 'categories')

    expect(Object.keys(await sentBody())).toEqual(['categories'])
  })

  it('sends the model on its own, once it differs from the stored one', async () => {
    const { api } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockReset()
    vi.mocked(api.request).mockResolvedValue(check())

    const { container } = renderPage(check())
    const button = container.querySelector<HTMLButtonElement>('#prompt-check-model-save')!
    expect(button.disabled).toBe(true)

    type(container, '#prompt-check-model', 'mistral-moderation-2411')
    await Promise.resolve()
    expect(button.disabled).toBe(false)

    await submit(container, 'model')
    expect(await sentBody()).toEqual({ model: 'mistral-moderation-2411' })
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
    type(container, '#prompt-check-threshold-sexual', '1.4')
    await submit(container, 'categories')

    expect(api.request).not.toHaveBeenCalled()
    expect(getByText('Saisissez un nombre entre 0 et 1.')).toBeInTheDocument()
  })

  it('lets the model be saved even when a threshold is out of bounds', async () => {
    const { api } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockReset()
    vi.mocked(api.request).mockResolvedValue(check())

    const { container } = renderPage(check())
    type(container, '#prompt-check-threshold-sexual', '1.4')
    type(container, '#prompt-check-model', 'mistral-moderation-2411')
    await submit(container, 'model')

    expect(await sentBody()).toEqual({ model: 'mistral-moderation-2411' })
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

  it('saves the switch as soon as it is toggled, and nothing else with it', async () => {
    const { api } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockReset()
    vi.mocked(api.request).mockResolvedValue(check())

    const { container } = renderPage(check())
    const toggle = container.querySelector<HTMLInputElement>('#prompt-check-enabled')!
    expect(toggle.checked).toBe(true)
    toggle.checked = false
    toggle.dispatchEvent(new Event('change', { bubbles: true }))
    await Promise.resolve()

    expect(api.request).toHaveBeenCalledWith(
      '/admin/prompt-check',
      expect.objectContaining({ method: 'PATCH' })
    )
    expect(await sentBody()).toEqual({ enabled: false })
  })

  it('puts the switch back when the save fails', async () => {
    const { api } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockReset()
    vi.mocked(api.request).mockRejectedValue(new Error('Le serveur n’a pas répondu'))

    const { container } = renderPage(check())
    const toggle = container.querySelector<HTMLInputElement>('#prompt-check-enabled')!
    toggle.checked = false
    toggle.dispatchEvent(new Event('change', { bubbles: true }))
    await Promise.resolve()
    await Promise.resolve()
    await Promise.resolve()

    expect(toggle.checked).toBe(true)
  })

  it('says nothing is checked while the switch is off, without locking the rules', async () => {
    const { container, getByText } = renderPage(check({ enabled: false }))

    expect(
      getByText(/aucun message n'est vérifié, quelles que soient les règles ci-dessous/)
    ).toBeInTheDocument()
    expect(
      container.querySelector<HTMLInputElement>('#prompt-check-action-sexual-block')?.disabled
    ).toBe(false)
    expect(
      container.querySelector<HTMLInputElement>('#prompt-check-threshold-sexual')?.disabled
    ).toBe(false)
  })

  it('sends the key on its own, once it has been replaced', async () => {
    const { api } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockReset()
    vi.mocked(api.request).mockResolvedValue(check({ has_api_key: true }))

    const { container } = renderPage(check({ has_api_key: true }))
    container.querySelector<HTMLButtonElement>('#prompt-check-api-key-replace')!.click()
    await Promise.resolve()
    type(container, '#prompt-check-api-key', 'nouvelle-cle')
    await submit(container, 'api-key')

    expect(await sentBody()).toEqual({ api_key: 'nouvelle-cle' })
  })

  it('shows a stored key as dots, with no field until replacing is chosen', async () => {
    const { container } = renderPage(check({ has_api_key: true }))

    expect(container.querySelector('#prompt-check-api-key-state')?.textContent?.trim()).toBe(
      'Clé enregistrée'
    )
    const masked = container.querySelector('#prompt-check-api-key-masked')!
    expect(masked.textContent?.trim()).toBe('••••••••••••')
    expect(masked.tagName).toBe('P')
    expect(container.querySelector('#prompt-check-api-key')).not.toBeInTheDocument()

    container.querySelector<HTMLButtonElement>('#prompt-check-api-key-replace')!.click()
    await Promise.resolve()

    const field = container.querySelector<HTMLInputElement>('#prompt-check-api-key')!
    expect(field.value).toBe('')
    expect(field.type).toBe('password')
    expect(field.getAttribute('autocomplete')).toBe('off')
    expect(container.querySelector('#prompt-check-api-key-masked')).not.toBeInTheDocument()

    // Champ vide : l'enregistrement effacera la clé stockée.
    expect(container.querySelector('#prompt-check-api-key-clearing')).toBeInTheDocument()

    container.querySelector<HTMLButtonElement>('#prompt-check-api-key-cancel')!.click()
    await Promise.resolve()
    expect(container.querySelector('#prompt-check-api-key')).not.toBeInTheDocument()
    expect(container.querySelector('#prompt-check-api-key-masked')).toBeInTheDocument()
  })

  it('says when no key is stored and offers the field right away', () => {
    const { container } = renderPage(check())

    expect(container.querySelector('#prompt-check-api-key-state')?.textContent?.trim()).toBe(
      'Aucune clé enregistrée'
    )
    expect(container.querySelector('#prompt-check-api-key')).toBeInTheDocument()
    expect(container.querySelector('#prompt-check-api-key-masked')).not.toBeInTheDocument()
    expect(container.querySelector('#prompt-check-api-key-replace')).not.toBeInTheDocument()
  })

  it('stays readable when the counts are missing', () => {
    const { getByText } = renderPage(check())

    expect(getByText('Les compteurs ne sont pas disponibles pour le moment.')).toBeInTheDocument()
  })
})
