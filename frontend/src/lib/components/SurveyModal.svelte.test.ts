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
  const actual = await importOriginal()
  return {
    ...actual,
    getSurveyContext: () => ({
      voteQuestions: mocks.questions
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

const paths = () => mocks.request.mock.calls.map(([path]) => path)

// The DSFR script is what discloses and conceals the dialog in the browser;
// in tests a conceal event stands in for Escape, the backdrop or the close
// button, all of which reach onClose the same way.
function conceal(container: HTMLElement) {
  fireEvent(container.querySelector('dialog')!, new Event('dsfr.conceal', { bubbles: true }))
}

const callsTo = (path: string) => mocks.request.mock.calls.filter(([called]) => called === path)
const bodyOf = (call: unknown[]) => JSON.parse((call[1] as RequestInit).body as string)

async function openModal() {
  const result = render(SurveyModal)
  // The popup lands a moment after mounting, and counts as shown right then.
  await waitFor(() => expect(paths()).toContain('/survey/dismiss'), { timeout: 6000 })
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

  it('counts every question as shown when the popup lands', async () => {
    await openModal()

    expect(callsTo('/survey/dismiss')).toHaveLength(1)
    expect(bodyOf(callsTo('/survey/dismiss')[0])).toEqual({ question_ids: ['q1', 'q2'] })
    expect(paths()).not.toContain('/survey/answers')
  }, 10000)

  it('saves selections once when closed without submitting', async () => {
    const { container } = await openModal()

    const first = container.querySelector<HTMLSelectElement>('#q1')!
    await fireEvent.change(first, { target: { value: 'q1-b' } })
    conceal(container)

    await waitFor(() => expect(paths()).toContain('/survey/answers'))
    expect(bodyOf(callsTo('/survey/answers')[0])).toEqual({
      answers: [{ question_id: 'q1', option_keys: ['q1-b'] }]
    })

    // One save total even if close fires again, and the showing is not
    // counted a second time.
    conceal(container)
    await new Promise((resolve) => setTimeout(resolve, 0))
    expect(callsTo('/survey/answers')).toHaveLength(1)
    expect(callsTo('/survey/dismiss')).toHaveLength(1)
  }, 10000)

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
    expect(callsTo('/survey/dismiss')).toHaveLength(1)
  }, 10000)
})
