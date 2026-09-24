import { describe, expect, it } from 'vitest'
import { buildUsageConsumption, USAGE_PROFILES } from './usageProfiles'

const actual = { inputTokens: 20, outputTokens: 80, totalTokens: 100, energyMwh: 5 }

describe('buildUsageConsumption', () => {
  it('preserves the measured consumption for the current discussion', () => {
    expect(buildUsageConsumption(USAGE_PROFILES.discussion, actual, 12)).toEqual(actual)
  })

  it('uses growing reference workloads and estimates energy from generated tokens only', () => {
    expect(buildUsageConsumption(USAGE_PROFILES.research, actual, 12)).toEqual({
      inputTokens: 250000,
      outputTokens: 60000,
      totalTokens: 310000,
      energyMwh: 720
    })
    expect(buildUsageConsumption(USAGE_PROFILES.coding, actual, 12)).toEqual({
      inputTokens: 450000,
      outputTokens: 50000,
      totalTokens: 500000,
      energyMwh: 600
    })
  })
})
