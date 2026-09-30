import { api } from '$lib/fastapi-client'
import { logger } from '$lib/logger.server'
import {
  DEFAULT_INFORMATIONAL_PAGES,
  normalizeInformationalPages,
  type InformationalPages
} from '$lib/informational-pages'

export async function loadInformationalPages(fetcher: typeof fetch): Promise<InformationalPages> {
  try {
    return normalizeInformationalPages(
      await api.request('/settings/legal/informational-pages', { fetch: fetcher })
    )
  } catch (error) {
    logger.warn('Failed to load informational legal pages', { error: `${error}` })
    return DEFAULT_INFORMATIONAL_PAGES
  }
}
