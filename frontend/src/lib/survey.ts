import type { FormCheckboxGroupProps, FormSelectProps } from '$components/form'
import type {
  MySurveyAnswer,
  PublicSurveyQuestion,
  PublicSurveyQuestionsResponse
} from '$lib/generated/backend'
import { m } from '$lib/i18n/messages'
import { fromEntries } from '$lib/utils/commons'
import { createContext } from 'svelte'

export type SurveyQuestion = PublicSurveyQuestion
export type { PublicSurveyQuestionsResponse }

export const emptySurveyQuestions: PublicSurveyQuestionsResponse = { questions: [] }

export const [getSurveyQuestionsContext, setSurveyQuestionsContext] =
  createContext<PublicSurveyQuestion[]>()

export function questionsToFormItems(questions: PublicSurveyQuestion[]) {
  return questions.map((q) => {
    const field = {
      id: q.id,
      label: q.label,
      required: q.required,
      options: q.options.map(({ label, key }) => ({ value: key, label }))
    }

    if (q.input_type === 'select') {
      const options = [
        {
          value: null,
          label: field.required
            ? m['survey.question.chooseOption']()
            : m['survey.profile.noAnswerOption']()
        },
        ...field.options
      ]
      return { ...field, options, component: 'select' } satisfies FormSelectProps
    } else {
      return { ...field, component: 'checkbox-group' } satisfies FormCheckboxGroupProps
    }
  })
}

export function answersToForm(answers: MySurveyAnswer[], questions: PublicSurveyQuestion[]) {
  return fromEntries(
    questions.map((q) => {
      const answer = answers.find((answer) => answer.question_id === q.id)
      const value = answer
        ? q.input_type === 'select'
          ? answer.selected_keys[0]
          : answer.selected_keys
        : null
      return [q.id, value]
    })
  )
}

export function formToAnswers(
  form: Record<string, string | string[] | null>,
  questions: PublicSurveyQuestion[]
) {
  return questions
    .map((field) => {
      const option_keys = form[field.id] ?? []
      return {
        question_id: field.id,
        option_keys: Array.isArray(option_keys) ? option_keys : option_keys ? [option_keys] : []
      }
    })
    .filter((answer) => answer.option_keys.length > 0)
}

/**
 * The backend already enforces the real re-ask rules (answered, shown count,
 * days since last shown) before it decides which questions to return. This
 * only stops the popup from reopening a second time in the same browser
 * session after it was already offered once, e.g. across several
 * comparisons in one sitting.
 */
const SHOWN_THIS_SESSION_KEY = 'comparia-survey-shown'

export function hasShownSurveyThisSession(): boolean {
  try {
    return sessionStorage.getItem(SHOWN_THIS_SESSION_KEY) === '1'
  } catch {
    return false
  }
}

export function markSurveyShownThisSession(): void {
  try {
    sessionStorage.setItem(SHOWN_THIS_SESSION_KEY, '1')
  } catch {
    // Private browsing or disabled storage: worst case the popup can show
    // again later this session, which is harmless.
  }
}
