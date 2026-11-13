/**
 * Simple cohort detection.
 */

import { browser } from '$app/environment'
import { getContext, setContext } from 'svelte'

export const COHORT_STORAGE_KEY = 'comparia-cohorts'

// Any well-formed name: a selection mode may target a cohort the code does not
// know. The backend keeps only the cohorts someone set up on the comparison.
const COHORT = /^[a-z0-9-]{1,50}$/

// Detect cohort from sessionStorage or URL parameters
function detectCohorts(): string {
  if (!browser) return ''

  const cohortsCommaSepareted = sessionStorage.getItem(COHORT_STORAGE_KEY)
  if (cohortsCommaSepareted) {
    console.debug(`[COHORT] Found in sessionStorage: '${cohortsCommaSepareted}'`)
    return cohortsCommaSepareted
  }
  // Detect from GET parameter
  const urlParams = new URLSearchParams(window.location.search)
  const cohortsCommaSeparetedParam = urlParams.get('c')
  if (!cohortsCommaSeparetedParam) return ''

  console.debug(`[COHORT] URL param c found: '${cohortsCommaSeparetedParam}'`)
  return parseCohortsParam(cohortsCommaSeparetedParam)
}

/** The well-formed cohorts in a `?c=` value, sorted so the backend always sees the same string. */
export function parseCohortsParam(param: string | null): string {
  if (!param) return ''
  const cohorts = param.split(',').filter((item) => COHORT.test(item))
  return cohorts
    .filter((item, index) => cohorts.indexOf(item) === index)
    .sort()
    .join(',')
}

/** The cohorts detected for this tab, or '' before detection or on the server. */
export function storedCohorts(): string {
  if (!browser) return ''
  return sessionStorage.getItem(COHORT_STORAGE_KEY) ?? ''
}

/**
 * Set cohort detection (client-side only)
 */
export function setCohortContext() {
  const cohortsCommaSeparetedParam = detectCohorts()
  const cohortsForLogging = cohortsCommaSeparetedParam || '(empty)'
  if (browser) {
    console.debug(`[COHORT] Storing in sessionStorage '${cohortsForLogging}'`)
    // Set cohorts even if it is an empty string, this allows to check that it is not
    // null and therefore detection has been called
    sessionStorage.setItem(COHORT_STORAGE_KEY, cohortsCommaSeparetedParam)
  }
  console.debug(`[COHORT] Setting context with '${cohortsForLogging}'`)
  setContext<string>(COHORT_STORAGE_KEY, cohortsCommaSeparetedParam)
}

/**
 * Get cohort context
 */
export function getCohortContext() {
  return getContext<string>(COHORT_STORAGE_KEY)
}
