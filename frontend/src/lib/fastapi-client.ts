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

  // /api: every backend route lives there (see backend/main.py) so it never
  // collides with a same-named SvelteKit page once both sit behind the same
  // host with no base path (e.g. /admin, /models, /settings are pages too).
  if (ssr) {
    // Server-side: use PUBLIC_API_LOCAL_URL for internal service communication
    return (
      (publicEnv.PUBLIC_API_LOCAL_URL || publicEnv.PUBLIC_API_URL || 'http://localhost:8001') +
      '/api'
    )
  } else if (dev || publicEnv.PUBLIC_API_DEV_MODE === 'true') {
    return (publicEnv.PUBLIC_API_URL || 'http://localhost:8008') + '/api'
  } else {
    // Client-side: use public URL or origin
    return (window.location.origin || publicEnv.PUBLIC_API_URL || 'http://localhost:8001') + '/api'
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

/** Sole event of the stream when a check asks the user to confirm the prompt. */
export interface SSEWarningEvent {
  type: 'warning'
  warnings: { kind: string; message: string }[]
  warning_token: string
}

export type SSEEvent =
  | SSEInitEvent
  | SSEUpdateEvent
  | SSECompleteEvent
  | SSEChunkEvent
  | SSEErrorEvent
  | SSEWarningEvent

export class InternalError extends Error {
  constructor(message: string) {
    super(message)
  }
}

/** Longer than the backend's longest provider timeout, but still terminal. */
export const SSE_INACTIVITY_TIMEOUT_MS = 90_000

export class StreamTimeoutError extends Error {
  constructor() {
    super('The response stream stopped sending data')
    this.name = 'StreamTimeoutError'
  }
}

type PydanticValidationError = { loc: string[]; msg: string }

export class ValidationError extends Error {
  errors?: PydanticValidationError[]

  constructor(errors: PydanticValidationError[] | string) {
    const simple = typeof errors === 'string'
    const message = simple ? errors : 'Error in form'
    super(message)
    this.errors = simple ? undefined : errors
    this.name = 'ValidationError'
  }
}

export class UnauthorizedError extends Error {
  constructor(key: string) {
    super(key)
    this.name = 'UnauthorizedError'
  }
}

/** Any error thrown by the client, carrying the HTTP status it came from. */
export type ApiError = Error & { status?: number }

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
  getUrl(path: string): string {
    return `${this.baseUrl}${path}`
  }

  async parseErrorResponse(
    response: Response,
    path: string,
    method: RequestInit['method'] = 'GET'
  ): Promise<ApiError> {
    const message = `Error ${response.status} [${method}](${path}): `
    const content = await response.text()
    let error: Error
    try {
      const detail = JSON.parse(content).detail
      if (response.status === 401 || response.status === 403) {
        error = new UnauthorizedError(detail)
      } else if (response.status === 422) {
        error = new ValidationError(detail)
      } else if (response.status === 429) {
        error = new ValidationError(detail)
      } else {
        error = new InternalError(message + detail)
      }
    } catch {
      error = new Error(message + content)
    }
    return Object.assign(error, { status: response.status })
  }

  /**
   * Make a single HTTP request (non-streaming)
   */
  async request<T>(
    path: string,
    options: RequestInit & { fetch?: typeof fetch } = { fetch }
  ): Promise<T> {
    const url = this.getUrl(path)
    // Get svelte load function's fetch or use default
    const _fetch = options.fetch ?? fetch
    delete options.fetch

    try {
      const response = await _fetch(url, {
        ...options,
        headers: options.headers ?? {
          'Content-Type': 'application/json'
        },
        credentials: 'include'
      })

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
    const controller = new AbortController()

    console.debug(`Streaming from ${path}`)

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body),
        credentials: 'include',
        signal: controller.signal
      })

      if (!response.ok) {
        throw await this.parseErrorResponse(response, path, 'POST')
      }

      // Read SSE stream
      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        let timer: ReturnType<typeof setTimeout> | undefined
        const timeout = new Promise<never>((_, reject) => {
          timer = setTimeout(() => reject(new StreamTimeoutError()), SSE_INACTIVITY_TIMEOUT_MS)
        })
        let result: ReadableStreamReadResult<Uint8Array>
        try {
          result = await Promise.race([reader.read(), timeout])
        } catch (error) {
          if (error instanceof StreamTimeoutError) {
            void reader.cancel(error).catch(() => undefined)
            controller.abort(error)
          }
          throw error
        } finally {
          clearTimeout(timer)
        }

        const { done, value } = result

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
