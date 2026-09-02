export type UsageProfileId = 'discussion' | 'research' | 'coding'

export interface UsageProfile {
  id: UsageProfileId
  inputTokens?: number
  outputTokens?: number
}

export interface UsageConsumption {
  inputTokens: number
  outputTokens: number
  totalTokens: number
  energyMwh: number
}

export const USAGE_PROFILES: Record<UsageProfileId, UsageProfile> = {
  discussion: { id: 'discussion' },
  research: {
    id: 'research',
    inputTokens: 250_000,
    outputTokens: 60_000
  },
  coding: {
    id: 'coding',
    inputTokens: 450_000,
    outputTokens: 50_000
  }
}

export function buildUsageConsumption(
  profile: UsageProfile,
  actual: UsageConsumption,
  whPerMillionToken: number
): UsageConsumption {
  if (profile.id === 'discussion') return actual

  const inputTokens = profile.inputTokens!
  const outputTokens = profile.outputTokens!
  return {
    inputTokens,
    outputTokens,
    totalTokens: inputTokens + outputTokens,
    energyMwh: (whPerMillionToken * outputTokens) / 1000
  }
}
