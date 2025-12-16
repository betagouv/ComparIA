import { env } from '$env/dynamic/public'
import type { FrontendLogRequest, LogEntry } from '$lib/logger'

type LogLevel = 'debug' | 'info' | 'warn' | 'error'

const LOG_LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3
}

class Logger {
  private service: string
  private backendQueue: LogEntry[] = []
  private batchSize = 10
  private flushInterval = 5000 // 5 secondes
  private flushTimer: number | null = null
  private minLevel: LogLevel = 'info'

  constructor(service = 'frontend') {
    this.service = service

    // Lire le debug mode depuis la variable d'environnement (comme le backend)
    if (env.PUBLIC_LANGUIA_DEBUG?.toLowerCase() === 'true') {
      this.minLevel = 'debug'
    }

    // Démarrer le timer de flush automatique
    this.startFlushTimer()
  }

  setLogLevel(level: LogLevel): void {
    this.minLevel = level
  }

  private shouldLog(level: LogLevel): boolean {
    return LOG_LEVELS[level] >= LOG_LEVELS[this.minLevel]
  }

  private startFlushTimer(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer)
    }

    this.flushTimer = setInterval(() => {
      this.flushToBackend()
    }, this.flushInterval)
  }

  private async flushToBackend(): Promise<void> {
    if (this.backendQueue.length === 0) return

    const logsToSend = [...this.backendQueue]
    this.backendQueue = []

    try {
      // Import dynamique pour éviter les dépendances circulaires
      const { api } = await import('$lib/api')

      // Créer la requête avec métadonnées
      const request: FrontendLogRequest = {
        logs: logsToSend,
        session_hash: (api as any).client?.session_hash,
        user_agent: typeof window !== 'undefined' ? window.navigator.userAgent : undefined
      }

      // Utiliser fetch directement pour éviter les dépendances circulaires
      const response = await fetch(`${api.url}/frontend_logs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(request)
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
    } catch (error) {
      // Fallback: stdout en cas d'échec
      console.log(
        JSON.stringify({
          timestamp: new Date().toISOString(),
          level: 'warn',
          service: this.service,
          message: `Failed to send logs to backend`,
          context: {
            error: (error as Error).message,
            fallbackLogsCount: logsToSend.length
          },
          type: 'log_forwarding'
        })
      )

      // Écrire les logs échoués vers stdout
      logsToSend.forEach((log) => {
        // Modifier le message pour inclure les informations de contexte si présentes
        let message = log.message
        if (log.context && log.context.cohorts) {
          message = `${log.message} cohorts ${log.context.cohorts}`
        }

        console.log(
          JSON.stringify({
            ...log,
            timestamp: log.timestamp || new Date().toISOString(),
            service: this.service,
            message: message
          })
        )
      })
    }
  }

  private writeLog(entry: LogEntry, sendToBackend = false): void {
    // Vérifier le niveau de log
    if (!this.shouldLog(entry.level as LogLevel)) {
      return
    }

    // Déterminer si ce log doit aller au backend
    const shouldSendToBackend = sendToBackend || entry.sendToBackend || false

    // Préparer l'entrée de log avec timestamp
    const logEntry = {
      timestamp: entry.timestamp || new Date().toISOString(),
      service: entry.service || this.service,
      level: entry.level,
      message: entry.message,
      context: entry.context
    }

    // Ajouter à la queue backend si nécessaire
    if (shouldSendToBackend) {
      this.backendQueue.push({ ...logEntry, sendToBackend: true })

      // Flush immédiat si la queue est pleine
      if (this.backendQueue.length >= this.batchSize) {
        this.flushToBackend()
      }
    }

    // Toujours écrire vers stdout
    if (env.PUBLIC_LOG_TO_STDOUT?.toLowerCase() === 'true') {
      let message = logEntry.message
      console.log(
        JSON.stringify({
          ...logEntry,
          message: message
        })
      )
    }
  }

  // Logs critiques envoyés au backend
  critical(message: string, context?: Record<string, any>): void {
    this.writeLog(
      {
        level: 'error',
        message,
        context: { ...context, priority: 'critical' }
      },
      true
    ) // sendToBackend = true
  }

  // Erreurs utilisateur importantes envoyées au backend
  userError(message: string, context?: Record<string, any>): void {
    this.writeLog(
      {
        level: 'error',
        message,
        context: { ...context, category: 'user_error' }
      },
      true
    ) // sendToBackend = true
  }

  // Actions utilisateur significatives envoyées au backend
  userAction(action: string, context?: Record<string, any>): void {
    this.writeLog(
      {
        level: 'debug',
        message: `User action: ${action}`,
        context: {
          type: 'user_action',
          action,
          ...context
        }
      },
      true
    ) // sendToBackend = true
  }

  // Méthodes standards (stdout uniquement par défaut, backend optionnel)
  error(message: string, context?: Record<string, any>, sendToBackend = false): void {
    this.writeLog(
      {
        level: 'error',
        message,
        context
      },
      sendToBackend
    )
  }

  warn(message: string, context?: Record<string, any>, sendToBackend = false): void {
    this.writeLog(
      {
        level: 'warn',
        message,
        context
      },
      sendToBackend
    )
  }

  info(message: string, context?: Record<string, any>, sendToBackend = false): void {
    this.writeLog(
      {
        level: 'info',
        message,
        context
      },
      sendToBackend
    )
  }

  debug(message: string, context?: Record<string, any>, sendToBackend = false): void {
    this.writeLog(
      {
        level: 'debug',
        message,
        context
      },
      sendToBackend
    )
  }

  // Méthode pour logger les requêtes API
  apiRequest(method: string, url: string, context?: Record<string, any>): void {
    this.writeLog({
      level: 'debug',
      message: `API ${method} ${url}`,
      context: {
        type: 'api_request',
        method,
        url,
        ...context
      }
    })
  }

  // Méthode pour logger les erreurs d'API critiques
  apiError(method: string, url: string, error: Error, context?: Record<string, any>): void {
    this.writeLog(
      {
        level: 'error',
        message: `API ${method} ${url} failed`,
        context: {
          type: 'api_error',
          method,
          url,
          error: error.message,
          stack: error.stack,
          ...context
        }
      },
      true
    ) // sendToBackend = true
  }

  // Forcer l'envoi des logs en attente (utilisé avant déchargement page)
  async flush(): Promise<void> {
    await this.flushToBackend()
    if (this.flushTimer) {
      clearInterval(this.flushTimer)
      this.flushTimer = null
    }
  }
}

export const logger = new Logger()
