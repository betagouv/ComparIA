import { api } from '$lib/api'
import type { VotesData } from '$lib/global.svelte'
import { getLocale } from '$lib/i18n/runtime'
import type { APIData } from '$lib/models'
import { error } from '@sveltejs/kit'

export async function load() {
  // Get the current locale using the runtime function
  const locale = getLocale()

  // Query votes depending on locale - only da or fr are valid for counter
  const counterLocale = locale === 'da' ? 'da' : 'fr'
  // Try to connect to the backend first
  let backendAvailable = true
  let _connectionError: Error | null = null

  try {
    await api._connect()
  } catch (err) {
    console.error('Failed to connect to backend:', err)
    backendAvailable = false
    _connectionError = err as Error

    // Return 503 error if we can't connect to backend
    throw error(503, 'Backend service unavailable')
  }

  // Try to fetch data from backend, but provide fallbacks if backend is down
  let votes: VotesData = { count: 0, objective: 0 }
  let data: APIData = { data_timestamp: Date.now() / 1000, models: [] }

  try {
    votes = await api.get<VotesData>(`/counter?c=${counterLocale}`)
  } catch (error) {
    console.warn('Backend is unavailable, using default votes:', error)
    // Use default values when backend is down
  }

  try {
    data = await api.get<APIData>('/available_models')
  } catch (error) {
    console.warn('Backend is unavailable, using default models:', error)
    // Use empty arrays when backend is down
  }

  return { data, votes, backendAvailable }
}
