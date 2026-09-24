import type { ScaleLogarithmic } from 'd3-scale'

/**
 * Ticks for a log axis: the round ones (1, 2 and 5 in each decade) so labels
 * stay apart, or a few of d3's own when the domain is too narrow to hold two
 * round ones.
 */
export function logTicks(scale: ScaleLogarithmic<number, number>): number[] {
  const round = scale.ticks().filter((tick) => {
    const mantissa = tick / 10 ** Math.floor(Math.log10(tick))
    return (
      Math.abs(mantissa - Math.round(mantissa)) < 1e-9 && [1, 2, 5].includes(Math.round(mantissa))
    )
  })

  return round.length >= 2 ? round : scale.ticks(4)
}
