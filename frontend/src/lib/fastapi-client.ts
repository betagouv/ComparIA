/**
 * FastAPI client for ComparIA backend.
 *
 * Replaces Gradio client with native HTTP/SSE implementation.
 */
import { browser, dev } from '$app/environment'
import { env as publicEnv } from '$env/dynamic/public'
import type { AssistantMessage, LLMPos, UserMessage } from '$lib/chatService.svelte'

// Function to get the appropriate backend URL
function getBackendUrl(): string {
  const ssr = !browser // browser false if SSR

  console.log('[DEBUG] getBackendUrl called', {
    browser,
    dev,
    ssr,
    PUBLIC_API_URL: publicEnv.PUBLIC_API_URL,
    PUBLIC_API_LOCAL_URL: publicEnv.PUBLIC_API_LOCAL_URL,
    'window.location.origin': browser ? window.location.origin : 'N/A (SSR)'
  })

  if (dev) {
    console.log('[DEBUG] Using dev URL: http://localhost:8001')
    return 'http://localhost:8001'
  } else if (ssr) {
    // Server-side: use PUBLIC_API_LOCAL_URL for internal service communication
    const url = publicEnv.PUBLIC_API_LOCAL_URL || publicEnv.PUBLIC_API_URL || 'http://localhost:8001'
    console.log('[DEBUG] Using SSR URL:', url)
    return url
  } else {
    // Client-side: use public URL if defined, otherwise same origin (reverse proxy)
    const url = window.location.origin || publicEnv.PUBLIC_API_URL || 'http://localhost:8001'
    console.log('[DEBUG] Using client URL:', url)
    return url
  }
}

/**
 * SSE event types from backend
 */
type SSEEventInit = { type: 'init'; session_hash: string }
type SSEEventChunk = { type: 'chunk'; pos: LLMPos; messages: Array<UserMessage | AssistantMessage> }
type SSEEventError = { type: 'error'; error: string; pos?: LLMPos } //; chat: APIChat }
type SSEEventComplete = { type: 'complete'; pos?: LLMPos }
export type AnySSEEvent = SSEEventInit | SSEEventError | SSEEventChunk | SSEEventComplete

interface SSEInitEvent {
  type: 'init'
  session_hash: string
}

interface SSEUpdateEvent {
  type: 'update'
  a: { messages?: any[] }
  b: { messages?: any[] }
}

interface SSEChunkEvent {
  type: 'chunk'
  messages: any[]
}

interface SSEDoneEvent {
  type: 'done'
}

interface SSEErrorEvent {
  type: 'error'
  error: string
}

export type SSEEvent = SSEInitEvent | SSEUpdateEvent | SSEChunkEvent | SSEDoneEvent | SSEErrorEvent

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

/**
 * FastAPI client class
 */
export class FastAPIClient {
  private baseUrl: string
  private sessionHash: string | null = null

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
   * Get current session hash (or retrieve from localStorage)
   */
  getSessionHash(): string | null {
    if (this.sessionHash) return this.sessionHash

    if (typeof window !== 'undefined' && window.sessionStorage) {
      const stored = sessionStorage.getItem('arena-session-hash')
      if (stored) {
        this.sessionHash = stored
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
    try {
      // Try to get json response
      const detail = (await response.json()).detail

      if (response.status === 422) {
        return new ValidationError(detail[0].msg)
      } else if (response.status === 429) {
        return new ValidationError(detail)
      } else {
        return new InternalError(message + detail)
      }
    } catch {
      // Not json try to get text, consider it unknown
      const content = await response.text()
      return new Error(message + content)
    }
  }

  /**
   * Set session hash and store in sessionStorage
   */
  setSessionHash(hash: string): void {
    this.sessionHash = hash
    if (typeof window !== 'undefined' && window.sessionStorage) {
      sessionStorage.setItem('arena-session-hash', hash)
    }
  }

  /**
   * Make a single HTTP request (non-streaming)
   */
  async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = this.getUrl(path)

    try {
      // Add session hash header if available
      const headers = new Headers(options.headers || {})
      if (this.sessionHash && !headers.has('X-Session-Hash')) {
        headers.set('X-Session-Hash', this.sessionHash)
      }

      const response = await fetch(url, {
        ...options,
        headers
      })

      if (!response.ok) {
        throw await this.parseErrorResponse(response, path, options.method)
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
  async *stream(path: string, body: any): AsyncGenerator<AnySSEEvent> {
    const url = this.getUrl(path)

    console.debug(`Streaming from ${path}`)

    try {
      // Add session hash header if available
      const headers: HeadersInit = {
        'Content-Type': 'application/json'
      }
      if (this.sessionHash) {
        headers['X-Session-Hash'] = this.sessionHash
      }

      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(body)
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
              if (data.type === 'init' && 'session_hash' in data) {
                // Store session hash from first event
                this.setSessionHash(data.session_hash)
              } else if (data.type === 'error') {
                // FIXME throw? probably not, errors are handle in chat
                // const errorMsg = 'error' in data ? data.error : 'Unknown error'
                // console.error(`SSE error: ${errorMsg}`)
                // useToast(errorMsg, 10000, 'error')
                // throw new Error(errorMsg)
              } else if (data.type === 'done') {
                // Stream complete
                console.debug('SSE stream completed')
                return
              }

              // Yield the parsed event
              yield data as AnySSEEvent
            } catch (_parseError) {
              console.error(`Failed to parse SSE data: ${dataStr}`)
            }
          }
        }
      }
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
