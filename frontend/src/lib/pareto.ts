export type ParetoPoint = { id: string; x: number; y: number }

/**
 * Ids of the points no other point beats on both axes, cheapest first.
 * Lower x is better, higher y is better. Two points at the same x keep only
 * the higher one; a point that merely ties the running best y is dominated.
 */
export function paretoFrontier(points: ParetoPoint[]): string[] {
  const sorted = [...points].sort((a, b) => a.x - b.x || b.y - a.y)
  const frontier: string[] = []
  let bestY = -Infinity

  for (const point of sorted) {
    if (point.y > bestY) {
      frontier.push(point.id)
      bestY = point.y
    }
  }

  return frontier
}
