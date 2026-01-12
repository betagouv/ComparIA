/**
 * Arena API wrapper for FastAPI backend.
 *
 * Provides typed methods for all arena endpoints.
 */

import { fastapiClient } from '$lib/fastapi-client'
import { logger } from '$lib/logger'
import { COHORT_STORAGE_KEY } from './stores/cohortStore.svelte'

/**
 * Selection mode for model pairing
 */
export type SelectionMode = 'random' | 'big-vs-small' | 'small-models' | 'custom'

/**
 * Arena-specific types
 */

export interface ChatUpdate {
  type: 'init' | 'update' | 'chunk' | 'done' | 'error'
  session_hash?: string
  a?: { messages?: any[] }
  b?: { messages?: any[] }
  messages?: any[]
  error?: string
}

export interface VoteResponse {
  success: boolean
  reveal: RevealData
}

export interface RevealData {
  model_a: string
  model_b: string
  model_a_metadata: any
  model_b_metadata: any
}

/**
 * Arena API methods
 */
export const arenaApi = {
  /**
   * Send first message and stream responses from both models
   */
  async *addFirstText(
    prompt: string,
    mode: SelectionMode,
    customModels?: [string, string]
  ): AsyncGenerator<ChatUpdate> {
    const cohorts = sessionStorage.getItem(COHORT_STORAGE_KEY)
    if (cohorts === null) {
      logger.error(
        `[COHORT] cohorts is None and it should not happen, maybe cohorts detection has not been called.`
      )
    }
    if (cohorts) {
      logger.debug(`[COHORT] call to '/arena/add_first_text' with found cohorts: '${cohorts}'`)
    }

    yield* fastapiClient.stream<ChatUpdate>('/arena/add_first_text', {
      prompt_value: prompt,
      mode,
      custom_models_selection: customModels || null,
      cohorts
    })
  },

  /**
   * Add a follow-up message and stream responses
   */
  async *addText(message: string): AsyncGenerator<ChatUpdate> {
    yield* fastapiClient.stream<ChatUpdate>('/arena/add_text', {
      message
    })
  },

  /**
   * Retry the last bot response
   */
  async *retry(): AsyncGenerator<ChatUpdate> {
    yield* fastapiClient.stream<ChatUpdate>('/arena/retry', {})
  },

  /**
   * Update reaction (like/dislike) for a message
   */
  async react(messageId: string, reaction: string | null): Promise<{ success: boolean }> {
    return fastapiClient.request('/arena/react', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message_id: messageId,
        reaction
      })
    })
  },

  /**
   * Submit vote and get reveal data
   */
  async vote(
    chosenModel: 'a' | 'b' | 'tie',
    preferences: Record<string, any> = {},
    comment?: string
  ): Promise<VoteResponse> {
    return fastapiClient.request<VoteResponse>('/arena/vote', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chosen_model: chosenModel,
        preferences,
        comment
      })
    })
  },

  /**
   * Get reveal data for a session
   */
  async reveal(sessionHash: string): Promise<RevealData> {
    return fastapiClient.request<RevealData>(`/arena/reveal/${sessionHash}`, {
      method: 'GET'
    })
  },

  /**
   * Get session hash from client
   */
  getSessionHash(): string | null {
    return fastapiClient.getSessionHash()
  }
}
