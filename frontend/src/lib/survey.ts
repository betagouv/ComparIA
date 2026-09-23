import type { FormCheckboxGroupProps, FormSelectProps } from '$components/form'
import type {
  MySurveyAnswer,
  MySurveyAnswersResponse,
  PublicSurveyQuestion,
  PublicSurveyQuestionsResponse
} from '$lib/generated/backend'
import { m } from '$lib/i18n/messages'
import { fromEntries } from '$lib/utils/commons'
import { createContext } from 'svelte'

export const emptySurveyQuestions: PublicSurveyQuestionsResponse = { questions: [] }
export const emptySurveyAnswers: MySurveyAnswersResponse = { answers: [] }

export type SurveyCtx = {
  show: boolean
  kind: 'signup' | 'after_vote' | null
  signupQuestions: PublicSurveyQuestion[]
  voteQuestions?: PublicSurveyQuestion[]
  signupAnswers: MySurveyAnswer[]
}
export const [getSurveyContext, setSurveyContext] = createContext<SurveyCtx>()

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

/**
 * The questions the profile page lists: every signup question, then every
 * other live question the person has answered, e.g. in the after-vote popup.
 * An option archived since it was chosen is kept on the question that holds
 * it, so the answer still shows, but is offered nowhere else.
 */
export function profileQuestions(
  questions: PublicSurveyQuestion[],
  answers: MySurveyAnswer[]
): PublicSurveyQuestion[] {
  const withHeldOptions = (question: PublicSurveyQuestion, answer?: MySurveyAnswer) => {
    const held = (answer?.options ?? []).filter(
      (option) =>
        answer!.selected_keys.includes(option.key) &&
        !question.options.some(({ key }) => key === option.key)
    )
    return held.length ? { ...question, options: [...question.options, ...held] } : question
  }

  const answerFor = (id: string) => answers.find((answer) => answer.question_id === id)
  const answeredElsewhere = answers
    .filter((answer) => !answer.archived && !questions.some((q) => q.id === answer.question_id))
    .map((answer) => ({
      id: answer.question_id,
      key: answer.question_key,
      // Only the signup form reads 'required'.
      required: false,
      input_type: answer.input_type,
      label: answer.label,
      revision: 0,
      options: answer.options.filter((option) => !option.archived)
    }))

  return [...questions, ...answeredElsewhere].map((question) =>
    withHeldOptions(question, answerFor(question.id))
  )
}

export function formToAnswers(
  form: Record<string, string | string[] | null>,
  questions: PublicSurveyQuestion[],
  filterEmpty = false
) {
  const answers = questions.map((field) => {
    const option_keys = form[field.id] ?? []
    return {
      question_id: field.id,
      option_keys: Array.isArray(option_keys) ? option_keys : option_keys ? [option_keys] : []
    }
  })

  if (filterEmpty) {
    return answers.filter((answer) => answer.option_keys.length > 0)
  }
  return answers
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
