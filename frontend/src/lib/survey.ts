import type { PublicSurveyQuestion, PublicSurveyQuestionsResponse } from '$lib/generated/backend'
import { createContext } from 'svelte'

export type SurveyQuestion = PublicSurveyQuestion
export type { PublicSurveyQuestionsResponse }

export const emptySurveyQuestions: PublicSurveyQuestionsResponse = { questions: [] }

export const [getSurveyQuestionsContext, setSurveyQuestionsContext] =
  createContext<SurveyQuestion[]>()

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
