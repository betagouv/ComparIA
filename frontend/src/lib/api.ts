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

/**
 * Extract the primary response data from a Gradio API response.
 *
 * Gradio API responses are tuples where the first element contains the actual data
 * returned from the Gradio function. This extracts that first element.
 */
function parseGradioResponse<T>(response: GradioPayload<T> | GradioResponse<T>): T {
  // Validate response has required data field
  // Note: Commented check for response.data.length was too strict (empty arrays are valid)
  if (!response.data || !Array.isArray(response.data)) {
    throw new Error('Invalid Gradio response format')
  }

  // Extract primary response (first element of Gradio data tuple)
  return response.data[0]
}

/**
 * Async generator that processes streaming Gradio responses and filters events.
 *
 * Converts the raw Gradio response stream into an async iterator of actual
 * response data, filtering out status events and handling errors.
 */
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

    // No load balancing configured, use single API endpoint
    if (replicas <= 0) {
      return '/api'
    }

    // Check if we have browser context with localStorage available
    if (typeof window !== 'undefined' && window.localStorage) {
      // Try to retrieve previously assigned endpoint for this session
      const storedEndpoint = localStorage.getItem('languia-api-endpoint')

      // If we have a stored endpoint and it's still valid, reuse it (session affinity)
      if (storedEndpoint) {
        const endpointNum = parseInt(storedEndpoint, 10)
        if (endpointNum >= 1 && endpointNum <= replicas) {
          return `/api/${endpointNum}`
        }
      }

      // Assign new endpoint: random number between 1 and replicas (inclusive)
      const randomEndpoint = Math.floor(Math.random() * replicas) + 1
      localStorage.setItem('languia-api-endpoint', randomEndpoint.toString())

      return `/api/${randomEndpoint}`
    }

    // Fallback for SSR or no localStorage: use first replica
    // this probably tend to overload this first replica
    return '/api/1'
  },

  /**
   * Connect to the Gradio backend server if not already connected.
   *
   * Establishes a persistent WebSocket connection to the Gradio client, which is required
   * for all subsequent API calls (submit, predict). Connection is reused across multiple
   * function calls to avoid redundant connections.
   */
  async _connect() {
    // Return cached connection if already established
    if (this.client) return this.client

    // Get the load-balanced endpoint (with session affinity)
    const endpoint = this._getLoadBalancedEndpoint()
    const fullUrl = window.location.origin + endpoint

    console.debug('Connecting to Gradio at:', fullUrl)
    try {
      // Connect to Gradio with event subscriptions for real-time updates
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

  /**
   * Submit an asynchronous Gradio function call and stream responses.
   *
   * Used for long-running operations that return multiple updates via streaming,
   * particularly for token-by-token AI model generation. Yields individual data
   * events as they arrive from the backend.
   *
   * This is the primary method for calling LLM inference endpoints that stream responses.
   *
   * Parameters:
   *   uri: Gradio function name or endpoint (e.g., "chat", "bot_response")
   *   params: Input parameters as key-value pairs for the Gradio function
   *
   * Returns:
   *   Promise<AsyncIterable<T>>: Resolves to async generator yielding responses
   *     - Each yield represents one streamed response from the backend
   *     - Can iterate with: for await (const response of result) { ... }
   *
   * Throws:
   *   Error: If submission fails or backend returns error status
   *     - Network errors automatically logged to console
   *     - Backend errors trigger toast notification to user
   *
   * Streaming Behavior:
   * 1. Submit request to Gradio backend
   * 2. Receive AsyncIterable that streams updates
   * 3. Filter events: skip 'status' events, yield 'data' events
   * 4. Convert each Gradio payload to user-friendly response (extract response.data[0])
   * 5. If backend returns error → throw Error + show toast notification
   */
  async submit<T>(uri: string, params: Record<string, unknown> = {}): Promise<AsyncIterable<T>> {
    console.debug(`Submitting Gradio job '${uri}' with params:`, params)

    try {
      // Get (or connect to) backend client
      const client = await this._connect()
      // Submit request and get streaming response iterable
      const result = await client.submit(uri, params)
      console.debug('Gradio job submitted successfully')
      // Filter and parse the streaming response data
      return iterGradioResponses(result as GradioSubmitIterable<T>)
    } catch (error) {
      console.error('Failed to submit Gradio job:', error)
      throw error
    }
  },

  /**
   * Call a Gradio function synchronously and wait for single response.
   *
   * Used for request-response operations that return a complete result in one call.
   * Unlike submit() which streams responses, predict() waits for completion and returns
   * the final result.
   *
   * Parameters:
   *   uri: Gradio function name or endpoint (e.g., "get_models", "check_status")
   *   params: Input parameters as key-value pairs for the Gradio function
   *
   * Returns:
   *   Promise<T>: Resolves to the response data from the backend
   *     - Type T is generic, inferred from call context
   *     - Automatically extracts first element from Gradio response tuple
   *
   * Throws:
   *   Error: If prediction fails or backend returns error status
   *     - Network errors automatically logged to console
   *     - Backend errors trigger toast notification to user
   *
   * Request-Response Flow:
   * 1. Connect to backend (if not already connected)
   * 2. Submit request to Gradio function
   * 3. Wait for response (blocks until complete)
   * 4. Extract and return result from Gradio response payload
   *
   * Differences from submit():
   * - predict(): Waits for single response, returns Promise<T>
   * - submit(): Streams multiple responses, returns Promise<AsyncIterable<T>>
   */
  async predict<T>(uri: string, params: Record<string, unknown> = {}): Promise<T> {
    console.debug(`Predicting Gradio job '${uri}' with params:`, params)

    try {
      // Get (or connect to) backend client
      const client = await this._connect()
      // Call Gradio function and wait for response
      const result = await client.predict(uri, params)
      console.debug('Gradio job predicted successfully')
      // Parse and return the response data
      return parseGradioResponse(result as GradioResponse<T>)
    } catch (error) {
      console.error('Failed to predict Gradio job:', error)
      throw error
    }
  },

  /**
   * Fetch JSON data via HTTP GET request.
   *
   * Low-level HTTP API for fetching data directly without Gradio client.
   * Used for static assets, configuration files, or non-Gradio endpoints.
   *
   * Unlike submit()/predict() which use Gradio/WebSocket, get() uses standard
   * HTTP fetch to retrieve JSON responses.
   */
  async get<T>(uri: string): Promise<T> {
    const url = this.url + uri
    return fetch(url).then(async (response) => {
      // Return parsed JSON if response is successful
      if (response.ok) return response.json()
      // Format error message with HTTP status and response body
      const message = `Error ${response.status} [GET](${url}): "${await response.text()}"`
      console.error(message)
      throw new Error(message)
    })
  }
}
