import SurveyModal from '$lib/components/SurveyModal.svelte'
import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  request: vi.fn(),
  questions: [] as Array<Record<string, unknown>>,
  user: null as Record<string, unknown> | null
}))

vi.mock('$lib/auth.svelte', () => ({
  getAuthContext: () => ({
    get user() {
      return mocks.user
    }
  })
}))

vi.mock('$app/navigation', async (importOriginal) => ({
  ...(await importOriginal<typeof import('$app/navigation')>()),
  invalidate: vi.fn()
}))

vi.mock('$lib/fastapi-client', () => ({
  api: { request: mocks.request }
}))

vi.mock('$lib/survey.svelte', async (importOriginal) => {
  const actual = await importOriginal<typeof import('$lib/survey.svelte')>()
  return {
    ...actual,
    getSurveyContext: () => ({
      questions: mocks.questions,
      unansweredQuestions: mocks.questions,
      answers: [],
      showSurveyCard: true
    }),
    hasShownSurveyThisSession: () => false,
    markSurveyShownThisSession: vi.fn()
  }
})

const question = (id: string) => ({
  id,
  key: `q-${id}`,
  required: false,
  input_type: 'select',
  label: `Question ${id}`,
  revision: 1,
  options: [
    { key: `${id}-a`, label: 'Option A' },
    { key: `${id}-b`, label: 'Option B' }
  ]
})

const callsTo = (path: string) => mocks.request.mock.calls.filter(([called]) => called === path)
const bodyOf = (call: unknown[]) => JSON.parse((call[1] as RequestInit).body as string)

describe('SurveyModal recording', () => {
  beforeEach(() => {
    mocks.questions = [question('q1'), question('q2')]
    mocks.request.mockResolvedValue(undefined)
    Object.defineProperty(window, 'dsfr', {
      configurable: true,
      value: () => ({ modal: { disclose: vi.fn(), conceal: vi.fn() } })
    })
  })

  afterEach(() => {
    mocks.questions = []
  })

  it('keeps the popup open with an error notice when submit fails, then retries', async () => {
    const { container } = render(SurveyModal)

    mocks.request.mockImplementation(() => Promise.reject(new Error('offline')))

    const first = container.querySelector<HTMLSelectElement>('#q1')!
    await fireEvent.change(first, { target: { value: 'q1-b' } })

    const submit = [...container.querySelectorAll<HTMLButtonElement>('button')].find(
      (button) => button.textContent?.trim() === 'Envoyer mes réponses'
    )!
    await fireEvent.click(submit)
    await waitFor(() => expect(container.querySelector('[role="alert"]')).not.toBeNull())
    // Still open for another try.
    expect(container.querySelector('dialog')).not.toBeNull()

    mocks.request.mockResolvedValue(undefined)
    await fireEvent.click(submit)
    await waitFor(() => expect(container.querySelector('[role="alert"]')).toBeNull())
    expect(callsTo('/survey/answers')).toHaveLength(2)
  }, 10000)
})

describe('SurveyModal answers', () => {
  beforeEach(() => {
    mocks.questions = [{ ...question('q1'), required: true }, question('q2')]
    mocks.request.mockResolvedValue(undefined)
  })

  it('sends what was answered even when a signup-required question is left blank', async () => {
    const { container } = render(SurveyModal)

    expect(container.querySelector('#q1')?.hasAttribute('required')).toBe(false)
    await fireEvent.change(container.querySelector<HTMLSelectElement>('#q2')!, {
      target: { value: 'q2-a' }
    })
    const submit = [...container.querySelectorAll<HTMLButtonElement>('button')].find(
      (button) => button.textContent?.trim() === 'Envoyer mes réponses'
    )!
    await fireEvent.click(submit)

    await waitFor(() => expect(callsTo('/survey/answers')).toHaveLength(1))
    expect(bodyOf(callsTo('/survey/answers')[0])).toEqual({
      answers: [
        { question_id: 'q1', value: null },
        { question_id: 'q2', value: 'q2-a' }
      ]
    })
  }, 10000)
})

describe('SurveyModal dismissal', () => {
  beforeEach(() => {
    mocks.questions = [{ ...question('q1'), required: true }, question('q2')]
    mocks.request.mockResolvedValue(undefined)
    Object.defineProperty(window, 'dsfr', {
      configurable: true,
      value: () => ({ modal: { disclose: vi.fn(), conceal: vi.fn() } })
    })
  })

  afterEach(() => {
    mocks.questions = []
    mocks.user = null
  })

  const close = (container: HTMLElement) =>
    container.querySelector('dialog')!.dispatchEvent(new CustomEvent('dsfr.conceal'))

  it('counts a close without answers as one showing of every question', async () => {
    const { container } = render(SurveyModal)

    close(container)

    await waitFor(() => expect(callsTo('/survey/answers')).toHaveLength(1))
    expect(bodyOf(callsTo('/survey/answers')[0])).toEqual({
      answers: [
        { question_id: 'q1', value: null },
        { question_id: 'q2', value: null }
      ]
    })
  })

  it('leaves the required questions of a signed-in account to the locked popup', async () => {
    mocks.user = { id: 'u1' }
    const { container } = render(SurveyModal)

    close(container)

    await waitFor(() => expect(callsTo('/survey/answers')).toHaveLength(1))
    expect(bodyOf(callsTo('/survey/answers')[0])).toEqual({
      answers: [{ question_id: 'q2', value: null }]
    })
  })

  it('does not count the close that follows a submit', async () => {
    const { container } = render(SurveyModal)
    const submit = [...container.querySelectorAll<HTMLButtonElement>('button')].find(
      (button) => button.textContent?.trim() === 'Envoyer mes réponses'
    )!
    await fireEvent.click(submit)
    await waitFor(() => expect(callsTo('/survey/answers')).toHaveLength(1))

    close(container)

    await new Promise((resolve) => setTimeout(resolve, 0))
    expect(callsTo('/survey/answers')).toHaveLength(1)
  })
})
