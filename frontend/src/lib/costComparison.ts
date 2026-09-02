export type CostComparison =
  | { kind: 'more' | 'less'; factor: number }
  | { kind: 'similar' }
  | { kind: 'unavailable' }

export function buildCostComparison(cost: number, otherCost: number): CostComparison {
  if (
    !Number.isFinite(cost) ||
    !Number.isFinite(otherCost) ||
    cost < 0 ||
    otherCost < 0 ||
    (otherCost === 0 && cost > 0)
  ) {
    return { kind: 'unavailable' }
  }

  if (cost === otherCost) return { kind: 'similar' }
  if (cost === 0) return { kind: 'unavailable' }

  const factor = Math.max(cost, otherCost) / Math.min(cost, otherCost)
  if (factor < 1.1) return { kind: 'similar' }

  return { kind: cost > otherCost ? 'more' : 'less', factor: Math.round(factor * 10) / 10 }
}
