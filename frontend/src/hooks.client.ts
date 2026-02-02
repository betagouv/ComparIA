import { env } from '$env/dynamic/public'
import * as Sentry from '@sentry/sveltekit'
import { handleErrorWithSentry } from '@sentry/sveltekit'

if (env.PUBLIC_SENTRY_FRONT_DSN) {
  Sentry.init({
    dsn: env.PUBLIC_SENTRY_FRONT_DSN,
    tracesSampleRate: 1.0,
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,
    integrations: [
      Sentry.replayIntegration({
        maskAllText: false,
        blockAllMedia: false
      })
    ]
  })
}

export const handleError = handleErrorWithSentry()
