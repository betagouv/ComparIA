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

/** A readable key from a name, not one of `taken`. */
export function keyFrom(label: string, taken: string[]) {
  const base =
    label
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^[^a-z]+|_+$/g, '')
      .slice(0, 36) || 'critere'
  let key = base
  for (let n = 2; taken.includes(key); n++) key = `${base}_${n}`
  return key
}
