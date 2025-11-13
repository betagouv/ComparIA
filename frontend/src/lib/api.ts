import { browser, dev } from '$app/environment'
import { env } from '$env/dynamic/public'
import { useToast } from '$lib/helpers/useToast.svelte'
import { m } from '$lib/i18n/messages'
import type { Payload, StatusMessage } from '@gradio/client'
import { Client } from '@gradio/client'

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
export interface GradioSubmitIterable<T> extends AsyncIterable<GradioPayload<T> | StatusMessage> {
  [Symbol.asyncIterator](): AsyncIterator<GradioPayload<T> | StatusMessage>
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
    if (response.type === 'status') {
      if (response.success === false) {
        const message = response.message ?? m['errors.unknown']()
        useToast(message, 10000, 'error')
        throw new Error(message)
      }
    }
    if (response.type === 'data') {
      yield parseGradioResponse(response)
    }
  }
}

export const api = {
  url: dev ? 'http://localhost:8000' : browser ? '' : env.PUBLIC_API_URL,
  // url: env.PUBLIC_API_URL || 'http://localhost:8000',
  // FIXME shoud remove PUBLIC_API_URL on prod/stg/dev and set it for local dev only
  client: undefined as Client | undefined,

  _getLoadBalancedEndpoint(): string {
    const replicas = parseInt(env.PUBLIC_COMPARIA_LB_REPLICAS || '0', 10)

    if (replicas <= 0) {
      return '/api'
    }

    if (typeof window !== 'undefined' && window.localStorage) {
      const storedEndpoint = localStorage.getItem('languia-api-endpoint')

      if (storedEndpoint) {
        const endpointNum = parseInt(storedEndpoint, 10)
        if (endpointNum >= 1 && endpointNum <= replicas) {
          return `/api/${endpointNum}`
        }
      }

      const randomEndpoint = Math.floor(Math.random() * replicas) + 1
      localStorage.setItem('languia-api-endpoint', randomEndpoint.toString())

      return `/api/${randomEndpoint}`
    }

    return '/api/1'
  },

  async _connect() {
    if (this.client) return this.client

    const endpoint = this._getLoadBalancedEndpoint()
    const fullUrl = this.url + endpoint

    console.debug('Connecting to Gradio at:', fullUrl)
    try {
      this.client = await Client.connect(fullUrl, { events: ['data', 'status'] })
      console.debug(
        `Successfully connected to Gradio (session hash: ${this.client.session_hash}) using endpoint: ${endpoint}`
      )
      return this.client
    } catch (error) {
      console.error('Failed to connect to Gradio:', error)
      throw error
    }
  },

  async submit<T>(uri: string, params: Record<string, unknown> = {}): Promise<AsyncIterable<T>> {
    console.debug(`Submitting Gradio job '${uri}' with params:`, params)

    try {
      const client = await this._connect()
      const result = await client.submit(uri, params)
      console.debug('Gradio job submitted successfully')
      return iterGradioResponses(result as GradioSubmitIterable<T>)
    } catch (error) {
      console.error('Failed to submit Gradio job:', error)
      throw error
    }
  },

  async predict<T>(uri: string, params: Record<string, unknown> = {}): Promise<T> {
    console.debug(`Predicting Gradio job '${uri}' with params:`, params)

    try {
      const client = await this._connect()
      const result = await client.predict(uri, params)
      console.debug('Gradio job predicted successfully')
      return parseGradioResponse(result as GradioResponse<T>)
    } catch (error) {
      console.error('Failed to predict Gradio job:', error)
      throw error
    }
  },

  async get<T>(uri: string): Promise<T> {
    const url = this.url + uri
    return fetch(url).then(async (response) => {
      if (response.ok) return response.json()
      const message = `Error ${response.status} [GET](${url}): "${await response.text()}"`
      console.error(message)
      throw new Error(message)
    })
  }
}
