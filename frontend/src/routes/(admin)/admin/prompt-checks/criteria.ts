import type { PromptCheckCriterion } from '$lib/generated/admin'
import { m } from '$lib/i18n/messages'

type Action = PromptCheckCriterion['action']

export const actionOrder: Action[] = ['off', 'log', 'warn', 'block']

export const actionLabels: Record<Action, string> = {
  off: m['admin.promptChecks.actions.off'](),
  log: m['admin.promptChecks.actions.log'](),
  warn: m['admin.promptChecks.actions.warn'](),
  block: m['admin.promptChecks.actions.block']()
}

export function newCriterion(): PromptCheckCriterion {
  return {
    key: '',
    label: '',
    question: '',
    yes: '',
    no: '',
    threshold: 0.5,
    action: 'log',
    message: 'generic'
  }
}
