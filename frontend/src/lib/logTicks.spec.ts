import { scaleLog } from 'd3-scale'
import { describe, expect, it } from 'vitest'
import { logTicks } from './logTicks'

const scale = (domain: [number, number]) => scaleLog(domain, [1000, 72])

describe('logTicks', () => {
  it('keeps the 1, 2, 5 ticks over a wide domain', () => {
    expect(logTicks(scale([0.7, 150]))).toEqual([1, 2, 5, 10, 20, 50, 100])
  })

  it('falls back to d3 ticks when a narrow domain holds no round one', () => {
    const ticks = logTicks(scale([0.021, 0.045]))
    expect(ticks.length).toBeGreaterThanOrEqual(2)
    expect(ticks.every((tick) => tick > 0.021 && tick < 0.045)).toBe(true)
  })

  it('falls back when the domain holds a single round tick', () => {
    expect(logTicks(scale([0.07, 0.15])).length).toBeGreaterThanOrEqual(2)
  })
})
