import { m } from '$lib/i18n/messages'
import { describe, expect, it } from 'vitest'
import {
  blockedByTools,
  filterCriteria,
  ruleSummary,
  shortList,
  warningText,
  type Lookups
} from './summary'

const lookups: Lookups = {
  llms: new Map([
    ['m1', 'Mistral Small'],
    ['m2', 'Llama 3']
  ]),
  labs: new Map([['l1', 'Mistral AI']]),
  licenses: new Map()
}

describe('ruleSummary', () => {
  const sizes = { pool_a_size: 12, pool_b_size: 12 }

  it('says how many models a blind draw picks from, and the tools', () => {
    expect(ruleSummary({ visitor_picks: 0, tools_policy: 'none', tool_keys: [] }, sizes)).toBe(
      `${m['admin.selectionModes.summary.draw']({ count: 12 })} · ${m['admin.selectionModes.summary.noTools']()}`
    )
  })

  it('names both pools when side B has its own', () => {
    expect(
      ruleSummary(
        { visitor_picks: 0, pool_b: { params_max: 60 } },
        { pool_a_size: 3, pool_b_size: 5 }
      )
    ).toBe(m['admin.selectionModes.summary.drawSplit']({ a: 3, b: 5 }))
  })

  it('adds the pairing, the weighting, forced tools and a limited audience', () => {
    const summary = ruleSummary(
      {
        visitor_picks: 1,
        pairing: 'different_lab',
        sampling: 'fewer_votes',
        tools_policy: 'forced',
        tool_keys: ['web_search'],
        cohorts: ['pix']
      },
      sizes,
      (key) => (key === 'web_search' ? 'Web search' : key)
    )
    expect(summary.split(' · ')).toEqual([
      m['admin.selectionModes.summary.pickOne']({ count: 12 }),
      m['admin.selectionModes.summary.differentLab'](),
      m['admin.selectionModes.summary.fewerVotes'](),
      m['admin.selectionModes.summary.forcedTools']({ tools: 'Web search' }),
      m['admin.selectionModes.summary.audience']()
    ])
  })

  it('says nothing about tools when the visitor picks among all of them', () => {
    expect(ruleSummary({ visitor_picks: 2, tools_policy: 'visitor', tool_keys: [] }, sizes)).toBe(
      m['admin.selectionModes.summary.pickTwo']({ count: 12 })
    )
  })
})

describe('filterCriteria', () => {
  it('describes nothing for an empty filter', () => {
    expect(filterCriteria({}, lookups)).toEqual([])
  })

  it('names models and labs, and marks deleted ones', () => {
    const criteria = filterCriteria({ llm_ids: ['m1', 'gone'], lab_ids: ['l1'] }, lookups)
    expect(criteria.map((criterion) => criterion.fields)).toEqual([['llm_ids'], ['lab_ids']])
    expect(criteria[0].text).toBe(
      m['admin.selectionModes.criteria.llms']({
        names: `Mistral Small, ${m['admin.selectionModes.unknownItem']()}`
      })
    )
  })

  it('reads a parameter range as one criterion', () => {
    const [criterion] = filterCriteria({ params_min: 10, params_max: 60 }, lookups)
    expect(criterion.fields).toEqual(['params_min', 'params_max'])
    expect(criterion.text).toBe(
      m['admin.selectionModes.criteria.paramsRange']({ min: 10, max: 60 })
    )
  })

  it('reads yes, no and either apart', () => {
    expect(filterCriteria({ public_weights: false }, lookups)[0].text).toBe(
      m['admin.selectionModes.criteria.proprietary']()
    )
    expect(filterCriteria({ public_weights: null }, lookups)).toEqual([])
  })

  it("tells systems with their own tools from models that take the arena's", () => {
    expect(filterCriteria({ arena_tools: false, tags: ['legal'] }, lookups)).toEqual([
      {
        fields: ['tags', 'tags_match'],
        text: m['admin.selectionModes.criteria.tags']({ tags: 'legal' })
      },
      { fields: ['arena_tools'], text: m['admin.selectionModes.criteria.arenaToolsNo']() }
    ])
  })

  it('says "all" only when several tags must all match', () => {
    expect(filterCriteria({ tags: ['legal'], tags_match: 'all' }, lookups)[0].text).toBe(
      m['admin.selectionModes.criteria.tags']({ tags: 'legal' })
    )
    expect(filterCriteria({ tags: ['legal', 'fr'], tags_match: 'all' }, lookups)[0].fields).toEqual(
      ['tags', 'tags_match']
    )
  })
})

describe('shortList', () => {
  it('keeps three names and counts the rest', () => {
    expect(shortList(['a', 'b', 'c'])).toBe('a, b, c')
    expect(shortList(['a', 'b', 'c', 'd', 'e'])).toBe('a, b, c +2')
  })
})

describe('warningText', () => {
  it('speaks of "the models" when there is a single pool', () => {
    expect(warningText('pool_a_empty', false)).toBe(m['admin.selectionModes.warnings.poolEmpty']())
    expect(warningText('pool_a_empty', true)).toBe(m['admin.selectionModes.warnings.poolAEmpty']())
  })

  it('says a forced mode is off for want of a tool, not of a pair', () => {
    const blocked = blockedByTools({ tools_policy: 'forced' }, { viable: false, pairs: 12 })
    expect(blocked).toBe(true)
    expect(warningText('tool_not_offered', false, blocked)).toBe(
      m['admin.selectionModes.warnings.forcedToolsOff']()
    )
    expect(warningText('tool_not_offered', false)).toBe(
      m['admin.selectionModes.warnings.toolNotOffered']()
    )
    expect(blockedByTools({ tools_policy: 'forced' }, { viable: false, pairs: 0 })).toBe(false)
    expect(blockedByTools({ tools_policy: 'visitor' }, { viable: true, pairs: 3 })).toBe(false)
  })
})
