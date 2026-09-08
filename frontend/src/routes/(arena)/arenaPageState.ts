import type { Comparison } from '$lib/chatService.svelte'

export function shouldShowInitialPrompt(
  comparisonId: string | undefined,
  comparison: Comparison | null
): boolean {
  return !comparisonId || !comparison?.turns.length
}
