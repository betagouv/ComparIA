/**
 * Simple cohort detection utilities.
 * This provides the getCurrentCohorts function used by the API.
 */
import { browser } from '$app/environment'
import { get } from 'svelte/store'
import { cohortStore } from '$lib/stores/cohortStore.svelte'
/**
 * Get current cohorts from the reactive state.
 * Returns array of cohort identifiers, primarily for backend communication.
 */
export function getCurrentCohorts(): string[] {
  if (!browser) return []
  const cohort = get(cohortStore)
  return cohort ? [cohort] : []
}
