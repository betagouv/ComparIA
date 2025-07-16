
import { state } from '$lib/state.svelte'
import type { Payload } from '@gradio/client'
import { Client } from '@gradio/client'
import { env } from '$env/dynamic/public'

export interface GradioPayload<T> extends Payload {
  type: 'data'
  endpoint: string
  // Tuple de 10 éléments où seul le premier nous intéresse
  data: [T, ...unknown[]]
}

interface GradioResponse<T> {
  type: 'data'
  time: Date
  endpoint: string
  fn_index: number
  // Tuple de 10 éléments où seul le premier nous intéresse
  data: [T, ...unknown[]]
}

// Gradio not exported
export interface GradioSubmitIterable<T> extends AsyncIterable<GradioPayload<T>> {
  [Symbol.asyncIterator](): AsyncIterator<GradioPayload<T>>
  cancel: () => Promise<void>
  event_id: () => string
}

function parseGradioResponse<T>(response: GradioPayload<T> | GradioResponse<T>): T {
  // if (!response.data || !Array.isArray(response.data) || response.data.length === 0) {
  if (!response.data || !Array.isArray(response.data)) {
    throw new Error('Invalid Gradio response format')
  }

  return response.data[0]
}

async function* iterGradioResponses<T>(responses: GradioSubmitIterable<T>): AsyncIterable<T> {
  for await (const response of responses) {
    if (response.type === 'data') {
      yield parseGradioResponse(response)
    }
  }
}

export const api = {
  url: env.PUBLIC_API_URL || '/api',
  client: undefined as Client | undefined,

  async _connect() {
    if (this.client) return this.client
    console.debug('Connecting to Gradio at:', this.url)
    try {
      this.client = await Client.connect(this.url)
      console.debug('Successfully connected to Gradio')
      return this.client
    } catch (error) {
      console.error('Failed to connect to Gradio:', error)
      throw error
    }
  },

  async submit<T>(uri: string, params: Record<string, unknown> = {}): Promise<AsyncIterable<T>> {
    state.loading = true
    console.debug(`Submitting Gradio job '${uri}' with params:`, params)

    try {
      const client = await this._connect()
      const result = await client.submit(uri, params)
      console.debug('Gradio job submitted successfully')
      return iterGradioResponses(result as GradioSubmitIterable<T>)
    } catch (error) {
      console.error('Failed to submit Gradio job:', error)
      throw error
    } finally {
      state.loading = false
    }
  },

  async predict<T>(uri: string, params: Record<string, unknown> = {}): Promise<T> {
    state.loading = true
    console.debug(`Predicting Gradio job '${uri}' with params:`, params)

    try {
      const client = await this._connect()
      const result = await client.predict(uri, params)
      console.debug('Gradio job predicted successfully')
      return parseGradioResponse(result as GradioResponse<T>)
    } catch (error) {
      console.error('Failed to predict Gradio job:', error)
      throw error
    } finally {
      state.loading = false
    }
  }
}
