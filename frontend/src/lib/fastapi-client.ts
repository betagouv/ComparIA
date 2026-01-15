/**
 * FastAPI client for ComparIA backend.
 *
 * Replaces Gradio client with native HTTP/SSE implementation.
 */

import { browser, dev } from '$app/environment'
import { env as publicEnv } from '$env/dynamic/public'
import type { AssistantMessage, LLMPos, UserMessage } from '$lib/chatService.svelte'
import { useToast } from '$lib/helpers/useToast.svelte'
import { logger } from '$lib/logger'

// Function to get the appropriate backend URL
function getBackendUrl(): string {
  const ssr = !browser // browser false if SSR

  if (dev) {
    return 'http://localhost:8001'
  } else if (ssr) {
    // Server-side: use PUBLIC_API_LOCAL_URL for internal service communication
    return publicEnv.PUBLIC_API_LOCAL_URL || publicEnv.PUBLIC_API_URL || 'http://localhost:8001'
  } else {
    // Client-side: use public URL or origin
    return window.location.origin || publicEnv.PUBLIC_API_URL || 'http://localhost:8001'
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
        const errorText = await response.text()
        const message = `Error ${response.status} [${options.method || 'GET'}](${path}): "${errorText}"`
        logger.error(`HTTP request failed: ${response.status} ${url} ${errorText}`)

        // Show toast for user-facing errors
        if (response.status === 429) {
          useToast('Rate limited', 10000, 'error')
        } else {
          useToast(errorText || message, 10000, 'error')
        }

        throw new Error(message)
      }

      return response.json()
    } catch (error) {
      logger.error(`Request to ${path} failed: ${(error as Error).message}`)
      throw error
    }
  }

  /**
   * Stream responses using Server-Sent Events (SSE)
   */
  async *stream(path: string, body: any): AsyncGenerator<AnySSEEvent> {
    const url = this.getUrl(path)

    logger.debug(`Streaming from ${path}`)

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
        const errorText = await response.text()
        logger.error(`Stream request failed: ${response.status} ${url} ${errorText}`)

        if (response.status === 429) {
          useToast('Rate limited', 10000, 'error')
        } else {
          // FIXME not sure to log the error
          // useToast(errorText, 10000, 'error')
        }

        throw new Error(`HTTP ${response.status}: ${errorText}`)
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
                // logger.error(`SSE error: ${errorMsg}`)
                // useToast(errorMsg, 10000, 'error')
                // throw new Error(errorMsg)
              } else if (data.type === 'done') {
                // Stream complete
                logger.debug('SSE stream completed')
                return
              }

              // Yield the parsed event
              yield data as AnySSEEvent
            } catch (_parseError) {
              logger.error(`Failed to parse SSE data: ${dataStr}`)
            }
          }
        }
      }
    } catch (error) {
      logger.error(`Stream from ${path} failed: ${(error as Error).message}`)
      throw error
    }
  }
}

/**
 * Global FastAPI client instance
 */
export const api = new FastAPIClient(getBackendUrl())
