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

const contentSafety: PromptCheckStatus = {
  kind: 'content_safety',
  mode: 'log',
  thresholds: { sexual: 0.3, criminal: 0.5 },
  model: 'mistral-moderation-latest',
  updated_at: '2026-07-01T10:00:00',
  consecutive_failures: 0,
  healthy: true
}
const pii: PromptCheckStatus = {
  kind: 'pii',
  mode: 'warn',
  thresholds: { pii: 0.5 },
  model: 'mistral-moderation-latest',
  updated_at: '2026-07-01T10:00:00',
  consecutive_failures: 7,
  healthy: false
}

const renderPage = (checks: PromptCheckStatus[]) =>
  render(Page, {
    data: { checks } as unknown as PageProps['data'],
    params: {} as PageProps['params']
  })

describe('admin prompt checks page', () => {
  it('saves a threshold the number input handed back as a number', async () => {
    const { api } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockResolvedValue(pii)

    const { container } = renderPage([pii])
    const field = container.querySelector<HTMLInputElement>('#prompt-check-pii-threshold-pii')!
    field.value = '0.65'
    field.dispatchEvent(new Event('input', { bubbles: true }))
    container.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true }))
    await Promise.resolve()

    expect(api.request).toHaveBeenCalledWith(
      '/admin/prompt-checks/pii',
      expect.objectContaining({ method: 'PATCH' })
    )
    const body = JSON.parse(vi.mocked(api.request).mock.calls[0][1]!.body as string)
    expect(body.thresholds).toEqual({ pii: 0.65 })
  })

  it('offers the four modes per check and preselects the stored one', () => {
    renderPage([contentSafety, pii])

    const modes = [...document.querySelectorAll('#prompt-check-content_safety-mode label')].map(
      (label) => label.textContent?.trim()
    )
    expect(modes).toEqual(['Désactivée', 'Journal', 'Avertissement', 'Blocage'])

    const logged = document.querySelector<HTMLInputElement>('#prompt-check-content_safety-mode-log')
    const warned = document.querySelector<HTMLInputElement>('#prompt-check-pii-mode-warn')
    expect(logged?.checked).toBe(true)
    expect(warned?.checked).toBe(true)
  })

  it('bounds every threshold field between 0 and 1', () => {
    renderPage([contentSafety])

    const field = document.querySelector<HTMLInputElement>(
      '#prompt-check-content_safety-threshold-sexual'
    )
    expect(field?.value).toBe('0.3')
    expect(field?.getAttribute('min')).toBe('0')
    expect(field?.getAttribute('max')).toBe('1')
  })

  it('shows the never-blocking categories rather than hiding them', () => {
    const { getAllByText } = renderPage([contentSafety])

    for (const label of ['Santé', 'Droit', 'Finance']) {
      expect(getAllByText(`${label} : Jamais bloquante`).length).toBe(1)
    }
    expect(
      document.querySelector('#prompt-check-content_safety-threshold-health')
    ).not.toBeInTheDocument()
  })

  it('says so when a check has stopped working, and stays quiet when it has not', () => {
    const { getByText, queryByText } = renderPage([contentSafety, pii])

    expect(getByText('Vérification hors service')).toBeInTheDocument()
    expect(getByText('7 échecs consécutifs')).toBeInTheDocument()
    expect(getByText('Vérification opérationnelle')).toBeInTheDocument()
    expect(queryByText('0 échecs consécutifs')).not.toBeInTheDocument()
  })
})
