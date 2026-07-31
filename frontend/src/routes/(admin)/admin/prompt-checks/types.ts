/**
 * Écrits à la main : ces deux réponses ne viennent d'aucune classe SQLModel,
 * donc le générateur ne les produit pas dans $lib/generated/admin.
 */

export type PromptCheckAction = 'off' | 'log' | 'warn' | 'block'

export type PromptCheckDecision = 'pass' | 'logged' | 'warned' | 'blocked' | 'error'

/** Réponse de POST /admin/prompt-check/try. */
export type PromptCheckTry = {
  decision: PromptCheckDecision
  scores: Record<string, number>
  triggered: Record<string, PromptCheckAction>
  message: string | null
  latency_ms: number
}

/** Réponse de GET /admin/prompt-check/stats. */
export type PromptCheckStats = {
  days: number
  total: number
  by_decision: Partial<Record<PromptCheckDecision, number>>
  by_category: Record<string, number>
  proceeded: number
  warnings_shown: number
}
