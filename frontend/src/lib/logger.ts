// Simplified frontend logger that sends minimal structured logs to backend
// Only sends level and message, with optional context for backend processing

import { browser } from '$app/environment'
import { env } from '$env/dynamic/public'

// Simple logger that sends logs to backend with minimal structure
export const logger = {
  // Send debug message to backend
  debug(message: string): void {
    if (env.PUBLIC_LANGUIA_DEBUG?.toLowerCase() === 'true') {
      this.sendLog('debug', message)
    }
  },

  // Send info message to backend
  info(message: string): void {
    this.sendLog('info', message)
  },

  // Send warning message to backend
  warn(message: string): void {
    this.sendLog('warn', message)
  },

  // Send error message to backend
  error(message: string): void {
    this.sendLog('error', message)
  },

  // Send log to backend with level and message
  async sendLog(level: string, message: string): Promise<void> {
    // Try to send to backend
    if (browser) {
      try {
        const { api } = await import('$lib/api')
        // Send even without session_hash for debugging
        const response = await fetch(`${api.url}/frontend_logs`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            level,
            message,
            session_hash: api.client?.session_hash || null,
            user_agent: window.navigator.userAgent
          })
        })

        if (!response.ok) {
          console.warn(`Failed to send log to backend: ${response.status}`)
        }
      } catch (error) {
        console.warn('Error sending log to backend:', error)
      }
    }

    // Always log to console for debugging
    if (env.PUBLIC_LOG_TO_STDOUT?.toLowerCase() === 'true') {
      console.log(JSON.stringify({ level, message }))
    }
  }
}
