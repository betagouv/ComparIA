import type { AdminPublishStatus } from '$lib/generated/admin'
import { m } from '$lib/i18n/messages'

export type Run = AdminPublishStatus['runs'][number]

export function formatDate(value: string | null) {
  if (!value) return ''
  // The API answers in UTC; an administrator reads their own clock.
  const date = new Date(value.endsWith('Z') ? value : `${value}Z`)
  return date.toLocaleString('fr-FR')
}

export function runStatus(run: Run) {
  if (run.finished_at === null) return m['admin.publishing.historyRunning']()
  return run.succeeded
    ? m['admin.publishing.historySucceeded']()
    : m['admin.publishing.historyFailed']()
}

export const runVariant = (run: Run) =>
  run.finished_at === null ? 'blue-ecume' : run.succeeded ? 'green' : 'orange'
