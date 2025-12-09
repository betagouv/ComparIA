/**
 * Simple cohort detection.
 */

import { browser } from '$app/environment'
import { getContext, setContext } from 'svelte'

const COHORT_TYPES = ['do-not-track'] as const
export type CohortType = (typeof COHORT_TYPES)[number] | null

const COHORT_STORAGE_KEY = 'comparia-cohort'

// Detect cohort from sessionStorage, referrer or URL parameters
function detectCohort(): CohortType {
  if (!browser) return null

  const sessionValue = sessionStorage.getItem(COHORT_STORAGE_KEY)
  if (sessionValue && COHORT_TYPES.includes(sessionValue as any)) {
    return sessionValue as CohortType
  }

  // Detect from referrer (pix.com)
  if (document.referrer) {
    try {
      const referrerUrl = new URL(document.referrer);
      // Strictly check the hostname
      if (referrerUrl.hostname === 'pix.com' || referrerUrl.hostname.endsWith('.pix.com')) {
          sessionStorage.setItem(COHORT_STORAGE_KEY, 'do-not-track')
        return 'do-not-track'
      }
    } catch (_e) {
      // Handle invalid URLs if necessary
      console.error('Invalid referrer URL');
    }
  }
  // Detect from GET parameter
  const urlParams = new URLSearchParams(window.location.search)
  const cohortParam = urlParams.get('c')

  if (cohortParam && (cohortParam === 'pix' || cohortParam === 'do-not-track')) {
    sessionStorage.setItem(COHORT_STORAGE_KEY, 'do-not-track')
    return cohortParam === 'pix' ? 'do-not-track' : cohortParam
  }

  return null
}

/**
 * Set cohort detection (client-side only)
 */
export function setCohortContext() {
  setContext<CohortType>(COHORT_STORAGE_KEY, detectCohort())
}

/**
 * Get cohort context
 */
export function getCohortContext() {
  return getContext<CohortType>(COHORT_STORAGE_KEY)
}

/**
 * Get current cohorts.
 * Returns array of cohort identifiers, primarily for backend communication.
 */
export function getCurrentCohorts(): string[] {
  const cohort = getCohortContext()
  return cohort ? [cohort] : []
}
