/**
 * Simple cohort detection using Svelte 5 state management.
 */

import { browser } from '$app/environment'
import { writable } from 'svelte/store'

export type CohortType = 'do-not-track' | null

const COHORT_STORAGE_KEY = 'comparia-cohort'

export const cohortStore = writable<CohortType>(null)

// Detect cohort from referrer or URL parameters
function detectCohort(): CohortType {
  if (!browser) return null

  // Detect from referrer (pix.com)
  if (document.referrer && document.referrer.includes('pix.com')) {
    return 'do-not-track'
  }

  // Detect from GET parameter
  const urlParams = new URLSearchParams(window.location.search)
  const cohortParam = urlParams.get('c')

  if (cohortParam && (cohortParam === 'pix' || cohortParam === 'do-not-track')) {
    return cohortParam === 'pix' ? 'do-not-track' : cohortParam
  }

  return null
}

/**
 * Initialize cohort detection - should be called once on app startup
 */
export function initializeCohortDetection(): CohortType {
  const detected = detectCohort()
  cohortStore.set(detected)
  return detected
}

/**
 * Set cohort context - used to programmatically set the cohort
 */
export function setCohortContext(cohort: CohortType): void {
  cohortStore.set(cohort)
}
