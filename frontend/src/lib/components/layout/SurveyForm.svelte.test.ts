import SurveyForm from '$lib/components/layout/SurveyForm.svelte'
import { fireEvent, render, waitFor } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => {
  const question = (id: string) => ({
    id,
    key: `q-${id}`,
    required: false,
    input_type: 'select' as const,
    label: `Question ${id}`,
    revision: 1,
    options: [
      { key: `${id}-a`, label: 'Option A', archived: false },
      { key: `${id}-b`, label: 'Option B', archived: false }
    ]
  })
  return { request: vi.fn(), question }
})

vi.mock('$lib/fastapi-client', () => ({
  api: { request: mocks.request }
}))

vi.mock('$app/navigation', async (importOriginal) => ({
  ...(await importOriginal<typeof import('$app/navigation')>()),
  invalidate: vi.fn()
}))

vi.mock('$lib/survey.svelte', async (importOriginal) => {
  const actual = await importOriginal<typeof import('$lib/survey.svelte')>()
  const questions = ['q1', 'q2', 'q3'].map(mocks.question)
  return {
    ...actual,
    getSurveyContext: () => ({
      questions,
      unansweredQuestions: [],
      answers: [
        {
          question_id: 'q1',
          question_key: 'q-q1',
          label: 'Question q1',
          input_type: 'select',
          options: questions[0].options,
          value: 'q1-a',
          archived: false
        }
      ],
      showSurveyCard: false
    })
  }
})

describe('SurveyForm on the profile page', () => {
  beforeEach(() => {
    mocks.request.mockReset()
    mocks.request.mockResolvedValue(undefined)
  })

  const submitOf = (container: HTMLElement) =>
    [...container.querySelectorAll<HTMLButtonElement>('button')].find(
      (button) => button.getAttribute('type') === 'submit'
    )!

  it('sends only the questions the person changed', async () => {
    const { container } = render(SurveyForm, { id: 'survey', title: 'Profil' })

    await fireEvent.change(container.querySelector<HTMLSelectElement>('#q2')!, {
      target: { value: 'q2-b' }
    })
    await fireEvent.click(submitOf(container))

    await waitFor(() => expect(mocks.request).toHaveBeenCalledTimes(1))
    expect(JSON.parse(mocks.request.mock.calls[0][1].body)).toEqual({
      answers: [{ question_id: 'q2', value: 'q2-b' }]
    })
  })

  it('sends nothing when nothing changed', async () => {
    const onSuccess = vi.fn()
    const { container } = render(SurveyForm, { id: 'survey', title: 'Profil', onSuccess })

    await fireEvent.click(submitOf(container))

    await waitFor(() => expect(onSuccess).toHaveBeenCalled())
    expect(mocks.request).not.toHaveBeenCalled()
  })
})
