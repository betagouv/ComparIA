/**
 * Simple cohort detection.
 */

import { browser } from '$app/environment'
import { logger } from '$lib/logger'
import { getContext, setContext } from 'svelte'

const COHORT_STORAGE_KEY = 'comparia-cohorts'

// for now possible cohort are just an hardcoded Array here - move to db ?
const EXISTING_COHORTS = ['pix']

// Detect cohort from sessionStorage or URL parameters
function detectCohorts(): string {
  if (!browser) return ''

  const cohortsCommaSepareted = sessionStorage.getItem(COHORT_STORAGE_KEY) ?? ''
  if (cohortsCommaSepareted) {
    logger.debug(`[COHORT] Found in sessionStorage ${cohortsCommaSepareted}`)
    return cohortsCommaSepareted
  }
  // Detect from GET parameter
  const urlParams = new URLSearchParams(window.location.search)
  const cohortsCommaSeparetedParam = urlParams.get('c') ?? ''
  logger.debug(`[COHORT] URL param c ${cohortsCommaSeparetedParam}`)

  const inputCohortList = cohortsCommaSeparetedParam.split(',')

  const validCohorts: string[] = inputCohortList.filter((item) => EXISTING_COHORTS.includes(item))
  logger.debug(`[COHORT] Valid cohorts after filtering ${validCohorts.join(',')}`)

  // rebuilding the string after sorting cohort names for consistant orders in the backend/db
  const validCohortsCommaSeparated = validCohorts.sort().join(',')

  if (cohortsCommaSeparetedParam) {
    logger.debug(`[COHORT] Storing in sessionStorage ${validCohortsCommaSeparated}`)
    sessionStorage.setItem(COHORT_STORAGE_KEY, validCohortsCommaSeparated)
  }

  return validCohortsCommaSeparated
}

/**
 * Set cohort detection (client-side only)
 */
export function setCohortContext() {
  const cohortsCommaSeparetedParam = detectCohorts()
  const cohortsForLogging = cohortsCommaSeparetedParam || '(empty)'
  logger.debug(`[COHORT] Setting context with ${cohortsForLogging}`)
  setContext<string>(COHORT_STORAGE_KEY, cohortsCommaSeparetedParam)
}

/**
 * Get cohort context
 */
export function getCohortContext() {
  return getContext<string>(COHORT_STORAGE_KEY)
}
