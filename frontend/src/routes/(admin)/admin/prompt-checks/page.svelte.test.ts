import type { PromptCheckStatus } from '$lib/generated/admin'
import { render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import type { PageProps } from './$types'
import Page from './+page.svelte'

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

const renderPage = (status: PromptCheckStatus) =>
  render(Page, {
    data: { check: status } as unknown as PageProps['data'],
    params: {} as PageProps['params']
  })

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
    renderPage(check())

    const options = [...document.querySelectorAll('#prompt-check-action-sexual option')].map(
      (option) => option.textContent?.trim()
    )
    expect(options).toEqual(['Désactivée', 'Journal', 'Avertissement', 'Blocage'])

    const sexual = document.querySelector<HTMLSelectElement>('#prompt-check-action-sexual')
    const pii = document.querySelector<HTMLSelectElement>('#prompt-check-action-pii')
    expect(sexual?.value).toBe('log')
    expect(pii?.value).toBe('warn')
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
    const action = document.querySelector<HTMLSelectElement>('#prompt-check-action-health')
    expect(action).toBeInTheDocument()
    expect(action?.value).toBe('off')
    expect(action?.disabled).toBe(false)
    expect(document.querySelector('#prompt-check-threshold-health')).toBeInTheDocument()
  })

  it('explains what the four actions do, warning included', () => {
    const { getByText } = renderPage(check())

    expect(getByText('Ce que font les quatre actions')).toBeInTheDocument()
    expect(getByText(/La personne peut envoyer quand même/)).toBeInTheDocument()
  })

  it('says so when the check has stopped working, and stays quiet when it has not', () => {
    const { getByText, queryByText, unmount } = renderPage(
      check({ healthy: false, consecutive_failures: 7 })
    )

    expect(getByText('Vérification hors service')).toBeInTheDocument()
    expect(getByText('7 échecs consécutifs')).toBeInTheDocument()
    unmount()

    const healthy = renderPage(check())
    expect(healthy.getByText('Vérification opérationnelle')).toBeInTheDocument()
    expect(queryByText('0 échecs consécutifs')).not.toBeInTheDocument()
  })
})
