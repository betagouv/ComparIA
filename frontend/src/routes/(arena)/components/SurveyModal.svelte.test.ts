import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import SurveyModal from './SurveyModal.svelte'

const mocks = vi.hoisted(() => ({
  request: vi.fn(),
  questions: [] as Array<Record<string, unknown>>
}))

vi.mock('$lib/fastapi-client', () => ({
  api: { request: mocks.request }
}))

vi.mock('$lib/survey', () => ({
  getSurveyQuestionsContext: () => mocks.questions,
  hasShownSurveyThisSession: () => false,
  markSurveyShownThisSession: vi.fn()
}))

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

async function openModal() {
  const result = render(SurveyModal)
  // The popup waits four seconds after mounting before it lands.
  await waitFor(() => expect(result.container.querySelector('dialog')).not.toBeNull(), {
    timeout: 6000
  })
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

  it('submits selections and only dismisses blanks when closed without submitting', async () => {
    const { container } = await openModal()

    const first = container.querySelector<HTMLSelectElement>('#survey-question-q1')!
    await fireEvent.change(first, { target: { value: 'q1-b' } })
    conceal(container)

    await waitFor(() => expect(paths()).toContain('/survey/answers'))
    const answersCall = mocks.request.mock.calls.find(([path]) => path === '/survey/answers')
    expect(JSON.parse((answersCall![1] as RequestInit).body as string)).toEqual({
      answers: [{ question_id: 'q1', option_keys: ['q1-b'] }]
    })
    const dismissCall = mocks.request.mock.calls.find(([path]) => path === '/survey/dismiss')
    expect(JSON.parse((dismissCall![1] as RequestInit).body as string)).toEqual({
      question_ids: ['q2']
    })

    // One recording pass total even if close fires again.
    conceal(container)
    await new Promise((resolve) => setTimeout(resolve, 0))
    expect(paths().filter((path) => path === '/survey/dismiss')).toHaveLength(1)
  }, 10000)

  it('keeps the popup open with an error notice when submit fails, then retries', async () => {
    const { container } = await openModal()

    mocks.request.mockImplementation((path: string) =>
      path === '/survey/dismiss' ? Promise.resolve(undefined) : Promise.reject(new Error('offline'))
    )

    const first = container.querySelector<HTMLSelectElement>('#survey-question-q1')!
    await fireEvent.change(first, { target: { value: 'q1-b' } })

    const submit = [...container.querySelectorAll<HTMLButtonElement>('button')].find(
      (button) => button.textContent?.trim() === 'Envoyer mes réponses'
    )!
    await fireEvent.click(submit)
    await waitFor(() => expect(container.querySelector('[role="alert"]')).not.toBeNull())
    // Still open for another try.
    expect(container.querySelector('dialog')).not.toBeNull()
    expect(paths()).not.toContain('/survey/dismiss')

    mocks.request.mockResolvedValue(undefined)
    await fireEvent.click(submit)
    await waitFor(() => expect(paths()).toContain('/survey/answers'))
    expect(paths()).toContain('/survey/dismiss')
    expect(container.querySelector('[role="alert"]')).toBeNull()
  }, 10000)
})
