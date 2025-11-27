/**
 * Simplified cohort detection using Svelte 5 state management.
 * 
 * This provides a minimal, reactive way to manage cohort detection state
 * with session-scoped persistence.
 */

import { browser } from '$app/environment'

export type CohortType = 'do-not-track' | null

const COHORT_STORAGE_KEY = 'comparia-cohort'
const FIRST_VISIT_KEY = 'comparia-first-visit-detected'

// Simple state object with all cohort information
const cohortState = $state({
    cohort: null as CohortType,
    hasDetected: false,
    isFirstVisit: true
})

// Initialize state from sessionStorage
function initializeFromStorage() {
    if (!browser) return

    try {
        const storedCohort = sessionStorage.getItem(COHORT_STORAGE_KEY) as CohortType
        const hasDetected = sessionStorage.getItem(FIRST_VISIT_KEY) === 'true'

        cohortState.cohort = storedCohort
        cohortState.hasDetected = hasDetected
        cohortState.isFirstVisit = !hasDetected
    } catch {
        // Silently fail if sessionStorage is not available
    }
}

// Save state to sessionStorage
function saveToStorage() {
    if (!browser) return

    try {
        if (cohortState.cohort) {
            sessionStorage.setItem(COHORT_STORAGE_KEY, cohortState.cohort)
        } else {
            sessionStorage.removeItem(COHORT_STORAGE_KEY)
        }

        if (cohortState.hasDetected) {
            sessionStorage.setItem(FIRST_VISIT_KEY, 'true')
        } else {
            sessionStorage.removeItem(FIRST_VISIT_KEY)
        }
    } catch {
        // Silently fail if sessionStorage is not available
    }
}

// Detect cohort from referrer or URL parameters
function detectCohortFromSources(): CohortType {
    if (!browser) return null

    // Detect from referrer (pix.com)
    const referrer = document.referrer
    if (referrer && referrer.includes('pix.com')) {
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
export function initializeCohortDetection(): void {
    initializeFromStorage()

    // Only run detection if not already done
    if (!cohortState.hasDetected) {
        const detectedCohort = detectCohortFromSources()

        cohortState.cohort = detectedCohort
        cohortState.hasDetected = true
        cohortState.isFirstVisit = false

        saveToStorage()
    }
}

/**
 * Get the current cohort value (reactive)
 */
export function getCohort(): CohortType {
    return cohortState.cohort
}

/**
 * Check if cohort detection has been performed (reactive)
 */
export function hasDetectedCohort(): boolean {
    return cohortState.hasDetected
}

/**
 * Check if this is the first visit (reactive)
 */
export function isFirstVisit(): boolean {
    return cohortState.isFirstVisit
}

/**
 * Clear cohort information from sessionStorage and state.
 * Useful for testing or manual reset.
 */
export function clearCohortData(): void {
    cohortState.cohort = null
    cohortState.hasDetected = false
    cohortState.isFirstVisit = true

    if (browser) {
        try {
            sessionStorage.removeItem(COHORT_STORAGE_KEY)
            sessionStorage.removeItem(FIRST_VISIT_KEY)
        } catch {
            // Silently fail if sessionStorage is not available
        }
    }
}


// Export the state object for direct reactive access
export { cohortState }