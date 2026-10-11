import type { FormCheckboxGroupProps, FormSelectProps } from '$components/form'
import { getAuthContext } from '$lib/authContext.svelte'
import type {
  MySurveyAnswer,
  PublicSurveyQuestion,
  PublicSurveyResponse
} from '$lib/generated/backend'
import { m } from '$lib/i18n/messages'
import { fromEntries } from '$lib/utils/commons'
import type { AnyFormItemProps } from '$lib/utils/form'
import { createContext } from 'svelte'

export const emptySurvey: PublicSurveyResponse = {
  questions: [],
  answers: [],
  never_answered_ids: []
}

export type SurveyCtx = {
  show: boolean
  questions: PublicSurveyQuestion[]
  answers: MySurveyAnswer[]
  hasNeverAnsweredQuestions: boolean
  unansweredQuestions: PublicSurveyQuestion[]
}
const [getSurveyContext, setSurveyContext] = createContext<SurveyCtx>()

export { getSurveyContext }

export function provideSurveyContext(source: () => PublicSurveyResponse) {
  const auth = getAuthContext()
  const data = $derived(source())
  const hasNeverAnsweredQuestions = $derived(!!data.never_answered_ids.length)
  const unansweredQuestions = $derived.by(() => {
    return data.questions.filter((q) => {
      if(data.never_answered_ids.includes(q.id)) return true
      return !data.answers.find((answer) => answer.question_id === q.id)
    })
  })
  // Show modal at page load if survey not fullfilled
  let showModal = $state(auth.user?.questionsAnswered === false)

  const state: SurveyCtx = {
    get show() {
      return showModal
    },
    set show(value: boolean) {
      showModal = value
    },
    get questions() {
      return data.questions
    },
    get hasNeverAnsweredQuestions() {
      return hasNeverAnsweredQuestions
    },
    get unansweredQuestions() {
      return unansweredQuestions
    },
    get answers() {
      return data.answers
    }
  }

  setSurveyContext(state)
  return state
}

export function questionsToFormItems(questions: PublicSurveyQuestion[], ignoreRequired: boolean = false) {
  return questions.map((q) => {
    const field = {
      id: q.id,
      label: q.label,
      required: ignoreRequired ? false : q.required,
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
      return [q.id, answer?.value ?? null]
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
        answer!.value.includes(option.key) &&
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

/** One error per required question left blank, keyed like the form. */
export function requiredErrors(
  form: Record<string, string | string[] | null>,
  questions: AnyFormItemProps[]
): Record<string, string> {
  return fromEntries(
    questions
      .filter((q) => q.required)
      .filter((q) => {
        const value = form[q.id]
        return Array.isArray(value) ? !value.length : !value
      })
      .map((q) => [q.id, m['survey.question.required']()])
  )
}

