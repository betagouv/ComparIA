/**
 * FastAPI client for ComparIA backend.
 *
 * Replaces Gradio client with native HTTP/SSE implementation.
 */
import { browser, dev } from '$app/environment'
import { env as publicEnv } from '$env/dynamic/public'
import type {
  APIComparison,
  APIComparisonTurn,
  AssistantMessage,
  Bot
} from '$lib/chatService.svelte'

// Function to get the appropriate backend URL
function getBackendUrl(): string {
  const ssr = !browser // browser false if SSR

  if (ssr) {
    // Server-side: use PUBLIC_API_LOCAL_URL for internal service communication
    return publicEnv.PUBLIC_API_LOCAL_URL || publicEnv.PUBLIC_API_URL || 'http://localhost:8001'
  } else if (dev || publicEnv.PUBLIC_API_DEV_MODE === 'true') {
    return publicEnv.PUBLIC_API_URL || 'http://localhost:8008'
  } else {
    // Client-side: use public URL or origin
    return window.location.origin || publicEnv.PUBLIC_API_URL || 'http://localhost:8001'
  }
}

/**
 * SSE event types from backend
 */
export interface SSEInitEvent {
  type: 'init'
  comparison: APIComparison
}

export interface SSEUpdateEvent {
  type: 'add' | 'update'
  turn: APIComparisonTurn
}

export interface SSECompleteEvent {
  type: 'complete'
  pos?: Bot
}

export interface SSEChunkEvent {
  type: 'chunk'
  pos: Bot
  llm_msg: AssistantMessage
}

export interface SSEErrorEvent {
  type: 'error'
  pos?: Bot
  error: string
}

export type SSEEvent =
  | SSEInitEvent
  | SSEUpdateEvent
  | SSECompleteEvent
  | SSEChunkEvent
  | SSEErrorEvent

export class InternalError extends Error {
  constructor(message: string) {
    super(message)
  }
}

export class ValidationError extends Error {
  constructor(message: string) {
    super(message)
  }
}

export class UnauthorizedError extends Error {
  constructor() {
    super('Unauthorized')
    this.name = 'UnauthorizedError'
  }
}

type UnauthorizedHandler = () => void
let unauthorizedHandler: UnauthorizedHandler | null = null

export function setUnauthorizedHandler(handler: UnauthorizedHandler): void {
  unauthorizedHandler = handler
}

/**
 * FastAPI client class
 */
export class FastAPIClient {
  private baseUrl: string
  private comparisonId: string | null = null

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  /**
   * Get full URL for an endpoint
   */
  private getUrl(path: string): string {
    return `${this.baseUrl}${path}`
  }

  /**
   * Get current comparison id (or retrieve from localStorage)
   */
  getComparisonId(): string | null {
    if (this.comparisonId) return this.comparisonId

    if (typeof window !== 'undefined' && window.sessionStorage) {
      const stored = sessionStorage.getItem('arena-comparison-id')
      if (stored) {
        this.comparisonId = stored
        return stored
      }
    }

    return null
  }

  async parseErrorResponse(
    response: Response,
    path: string,
    method: RequestInit['method'] = 'GET'
  ): Promise<Error> {
    const message = `Error ${response.status} [${method}](${path}): `
    const content = await response.text()
    try {
      const detail = JSON.parse(content).detail

      if (response.status === 422) {
        return new ValidationError(detail[0].msg)
      } else if (response.status === 429) {
        return new ValidationError(detail)
      } else {
        return new InternalError(message + detail)
      }
    } catch {
      return new Error(message + content)
    }
  }

  /**
   * Set comparison id and store in sessionStorage
   */
  setComparisonId(id: string): void {
    this.comparisonId = id
    if (typeof window !== 'undefined' && window.sessionStorage) {
      sessionStorage.setItem('arena-comparison-id', id)
    }
  }

  /**
   * Make a single HTTP request (non-streaming)
   */
  async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = this.getUrl(path)

    try {
      // Add comparison id header if available
      const headers = new Headers(options.headers || {})
      if (this.comparisonId && !headers.has('X-Comparison-Id')) {
        headers.set('X-Comparison-Id', this.comparisonId)
      }

      const response = await fetch(url, {
        ...options,
        headers,
        credentials: 'include'
      })

      if (response.status === 401) {
        unauthorizedHandler?.()
        throw new UnauthorizedError()
      }

      if (!response.ok) {
        throw await this.parseErrorResponse(response, path, options.method)
      }

      if (response.status === 204) {
        return undefined as T
      }

      return response.json()
    } catch (error) {
      console.error(`Request to ${path} failed: ${(error as Error).message}`)
      throw error
    }
  }

  /**
   * Stream responses using Server-Sent Events (SSE)
   */
  async *stream(path: string, body: any): AsyncGenerator<SSEEvent> {
    const url = this.getUrl(path)

    console.debug(`Streaming from ${path}`)

    try {
      const headers: HeadersInit = {
        'Content-Type': 'application/json'
      }
      // Add comparison id header if available
      if (this.comparisonId) {
        headers['X-Comparison-Id'] = this.comparisonId
      }

      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
        credentials: 'include'
      })

      if (!response.ok) {
        throw await this.parseErrorResponse(response, path, 'POST')
      }

      // Read SSE stream
      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()

        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim()
            if (!dataStr) continue

            try {
              const data = JSON.parse(dataStr) as SSEEvent

              // Handle special event types
              if (data.type === 'init') {
                // Store comparison id from first event
                this.setComparisonId(data.comparison.id)
              } else if (data.type === 'error') {
                // FIXME throw? probably not, errors are handle in chat
                // const errorMsg = 'error' in data ? data.error : 'Unknown error'
                // console.error(`SSE error: ${errorMsg}`)
                // useToast(errorMsg, 10000, 'error')
                // throw new Error(errorMsg)
              }

              // Yield the parsed event
              yield data
            } catch (_parseError) {
              console.error(`Failed to parse SSE data: ${dataStr}`)
            }
          }
        }
      }
      console.debug('SSE stream completed')
    } catch (error) {
      console.error(`Stream from ${path} failed: ${(error as Error).message}`)
      throw error
    }
  }
}

/**
 * Global FastAPI client instance
 */
export const api = new FastAPIClient(getBackendUrl())
