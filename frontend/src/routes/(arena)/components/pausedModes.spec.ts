import type { PausedModel } from '$lib/limits.svelte'
import { describe, expect, it } from 'vitest'
import { fullModes, pausedModes } from './pausedModes'

const models = [
  { id: 'gpt', params: 1000 },
  { id: 'claude', params: 800 },
  { id: 'gemma', params: 30 },
  { id: 'mistral-small', params: 24 }
]

function pausedFor(...ids: string[]): Map<string, PausedModel> {
  return new Map(
    ids.map((id, i) => [
      id,
      { id, reason: 'allowance', until: `2026-10-14T1${5 - i}:40:00.000Z` } as PausedModel
    ])
  )
}

describe('pausedModes', () => {
  it('pauses nothing while a pair can still be drawn', () => {
    expect(pausedModes(models, pausedFor('gpt')).size).toBe(0)
  })

  it('pauses David contre Goliath once every big model is paused, until the first is back', () => {
    const modes = pausedModes(models, pausedFor('gpt', 'claude'))

    expect([...modes]).toEqual([['big-vs-small', '2026-10-14T14:40:00.000Z']])
  })

  it('needs two different models when both sides come from one pool', () => {
    const modes = pausedModes(models, pausedFor('gemma'))

    expect([...modes.keys()]).toEqual(['small-models'])
  })

  it('tells the modes that full models alone leave with nothing', () => {
    const paused = new Map<string, PausedModel>([
      ['gpt', { id: 'gpt', reason: 'full', until: '2026-10-14T22:00:00.000Z' }],
      ['claude', { id: 'claude', reason: 'full', until: '2026-10-14T22:00:00.000Z' }],
      ['gemma', { id: 'gemma', reason: 'allowance', until: '2026-10-14T15:40:00.000Z' }]
    ])

    // Big models are full; the small pool lacks a second model only because
    // of an allowance pause.
    expect([...fullModes(models, paused)]).toEqual(['big-vs-small'])
  })

  it('leaves alone a mode that had no model before any pause', () => {
    const noBig = models.filter((llm) => llm.params < 100)

    expect(pausedModes(noBig, pausedFor('gemma')).has('big-vs-small')).toBe(false)
  })
})
