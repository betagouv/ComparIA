import SurveyModal from '$lib/components/SurveyModal.svelte'
import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  request: vi.fn(),
  questions: [] as Array<Record<string, unknown>>
}))

vi.mock('$lib/fastapi-client', () => ({
  api: { request: mocks.request }
}))

vi.mock('$lib/survey', async (importOriginal) => {
  const actual = await importOriginal<typeof import('$lib/survey.svelte')>()
  return {
    ...actual,
    getSurveyContext: () => ({
      questions: mocks.questions
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

async function openModal() {
  const result = render(SurveyModal)
  const buttonOpen = result.container.querySelector('button')!
  await fireEvent.click(buttonOpen)
  return result
}

describe('SurveyModal recording', () => {
  beforeEach(() => {
    mocks.questions = [question('q1'), question('q2')]
    mocks.request.mockResolvedValue(undefined)
  })

  afterEach(() => {
    mocks.questions = []
  })

  it('keeps the popup open with an error notice when submit fails, then retries', async () => {
    const { container } = await openModal()

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
    const { container } = await openModal()

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
      answers: [{ question_id: 'q2', value: 'q2-a' }]
    })
  }, 10000)
})
