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

type PydanticValidationError = { loc: string[]; msg: string }

export class ValidationError extends Error {
  errors: PydanticValidationError[] | string

  constructor(errors: PydanticValidationError[] | string) {
    super('Error in form')
    this.errors = errors
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

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  /**
   * Get full URL for an endpoint
   */
  private getUrl(path: string): string {
    return `${this.baseUrl}${path}`
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
        return new ValidationError(detail)
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
   * Make a single HTTP request (non-streaming)
   */
  async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = this.getUrl(path)

    try {
      const response = await fetch(url, {
        ...options,
        headers: options.headers ?? {
          'Content-Type': 'application/json'
        },
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
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
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
              if (data.type === 'error') {
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
