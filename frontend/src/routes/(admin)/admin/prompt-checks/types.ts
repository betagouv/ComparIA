import type { PromptCheckCriterion } from '$lib/generated/admin'

export type PromptCheckAction = PromptCheckCriterion['action']

export type PromptCheckMessage = NonNullable<PromptCheckCriterion['message']>

/**
 * Écrits à la main : ces réponses ne viennent d'aucune classe SQLModel,
 * donc le générateur ne les produit pas dans $lib/generated/admin.
 */

/** Response of GET /admin/prompt-check/models. */
export type PromptCheckModel = { id: string; name: string }

export type PromptCheckDecision = 'pass' | 'logged' | 'warned' | 'blocked' | 'error' | 'skipped'

/** Réponse de POST /admin/prompt-check/try. */
export type PromptCheckTry = {
  decision: PromptCheckDecision
  scores: Record<string, number>
  triggered: Record<string, PromptCheckAction>
  message: string | null
  latency_ms: number
  /** What the decision model said when `decision` is "error". */
  error: string | null
}

/** Réponse de GET /admin/prompt-check/stats. */
export type PromptCheckStats = {
  period: 'all' | '7d' | '30d' | '90d' | '365d'
  bucket: 'day' | 'week' | 'month'
  historical_total: number
  total: number
  by_decision: Partial<Record<PromptCheckDecision, number>>
  by_category: Record<string, Partial<Record<PromptCheckDecision, number>>>
  timeline: PromptCheckTimelinePoint[]
}

export type PromptCheckTimelinePoint = {
  date: string
  by_decision: Partial<Record<PromptCheckDecision, number>>
}
