import type { SelectionModeAdmin } from '$lib/generated/admin'
import { describe, expect, it } from 'vitest'
import {
  cleanFilter,
  openToEveryone,
  toForm,
  toModeKey,
  toRules,
  toUpsert,
  uniqueModeKey
} from './mode'

const saved: SelectionModeAdmin = {
  id: 'a1',
  key: 'big-vs-small',
  label: { en: 'Big vs small', fr: 'Grand contre petit' },
  short_label: {},
  description: { en: ' One of each ' },
  icon: 'i-ri-ruler-line',
  enabled: true,
  position: 2,
  is_default: false,
  visitor_picks: 0,
  pool_a: { params_min: 100 },
  pool_b: { params_max: 60 },
  pairing: 'any',
  sampling: 'uniform',
  tools_policy: 'none',
  tool_keys: ['web_search'],
  cohorts: ['pix'],
  locales: ['fr'],
  starts_at: '2026-12-01T09:30:00',
  ends_at: null,
  viability: { viable: true, pool_a_size: 3, pool_b_size: 4, pairs: 12 }
}

describe('toForm and toUpsert', () => {
  it('round-trips a saved mode, without its row fields', () => {
    const body = toUpsert(toForm(saved))
    expect(body).toEqual({
      key: 'big-vs-small',
      label: { en: 'Big vs small', fr: 'Grand contre petit' },
      short_label: {},
      description: { en: 'One of each' },
      icon: 'i-ri-ruler-line',
      enabled: true,
      is_default: false,
      visitor_picks: 0,
      pool_a: { params_min: 100 },
      pool_b: { params_max: 60 },
      pairing: 'any',
      sampling: 'uniform',
      // No tools at all, whatever was ticked before the policy changed.
      tools_policy: 'none',
      tool_keys: [],
      cohorts: ['pix'],
      locales: ['fr'],
      starts_at: '2026-12-01T09:30:00',
      ends_at: null
    })
  })

  it('shows times as a datetime-local input does', () => {
    expect(toForm(saved).starts_at).toBe('2026-12-01T09:30')
    expect(toForm(saved).ends_at).toBe('')
  })

  it('does not share objects with the mode it started from', () => {
    const form = toForm(saved)
    form.pool_a.params_min = 1
    form.label.en = 'Changed'
    expect(saved.pool_a?.params_min).toBe(100)
    expect(saved.label.en).toBe('Big vs small')
  })

  it('fills a template that only sets a few fields', () => {
    const form = toForm({ key: 'legal', label: { en: 'Legal' }, pool_a: { tags: ['legal'] } })
    expect(form).toMatchObject({
      icon: 'i-ri-dice-line',
      enabled: true,
      is_default: false,
      visitor_picks: 0,
      pool_b: null,
      tools_policy: 'visitor',
      cohorts: [],
      starts_at: ''
    })
  })

  it('drops languages left empty from the texts', () => {
    const form = toForm(saved)
    form.label.it = '   '
    expect(toUpsert(form).label).toEqual({ en: 'Big vs small', fr: 'Grand contre petit' })
  })
})

describe('toRules', () => {
  it('sends only what the draw reads', () => {
    const rules = toRules({ ...toForm(saved), tools_policy: 'forced' })
    expect(Object.keys(rules).sort()).toEqual([
      'pairing',
      'pool_a',
      'pool_b',
      'sampling',
      'tool_keys',
      'tools_policy',
      'visitor_picks'
    ])
    expect(rules.tool_keys).toEqual(['web_search'])
  })
})

describe('cleanFilter', () => {
  it('leaves out every criterion that is not set', () => {
    expect(
      cleanFilter({
        llm_ids: [],
        tags: [],
        tags_match: 'any',
        public_weights: null,
        params_min: undefined,
        // What a cleared number input hands back.
        params_max: '' as unknown as number,
        released_after: ''
      })
    ).toEqual({})
  })

  it('keeps false, zero and numbers typed as text', () => {
    expect(
      cleanFilter({
        eu_hostable: false,
        params_min: 0,
        top_ranked: '10' as unknown as number
      })
    ).toEqual({ eu_hostable: false, params_min: 0, top_ranked: 10 })
  })

  it('keeps "all" only when there are tags to match', () => {
    expect(cleanFilter({ tags_match: 'all' })).toEqual({})
    expect(cleanFilter({ tags: ['legal', 'fr'], tags_match: 'all' })).toEqual({
      tags: ['legal', 'fr'],
      tags_match: 'all'
    })
  })
})

describe('mode keys', () => {
  it('turns a label into a key the server accepts', () => {
    expect(toModeKey('Petit contre Grand !')).toBe('petit-contre-grand')
    expect(toModeKey('Écologie & sobriété')).toBe('ecologie-sobriete')
    expect(toModeKey('a'.repeat(80))).toHaveLength(50)
  })

  it('numbers a key already taken', () => {
    expect(uniqueModeKey('legal', ['random'])).toBe('legal')
    expect(uniqueModeKey('legal', ['legal', 'legal-2'])).toBe('legal-3')
    expect(uniqueModeKey('', [])).toBe('mode')
  })
})

describe('openToEveryone', () => {
  const now = Date.parse('2026-11-12T12:00:00Z')
  const open = { ...saved, cohorts: [], locales: [], starts_at: null }

  it('holds for a viable mode with no audience and no window', () => {
    expect(openToEveryone(open, now)).toBe(true)
  })

  it('fails for a mode limited to a cohort, a language or a window, or unable to draw', () => {
    expect(openToEveryone({ ...open, cohorts: ['pix'] }, now)).toBe(false)
    expect(openToEveryone({ ...open, locales: ['fr'] }, now)).toBe(false)
    expect(openToEveryone({ ...open, starts_at: '2026-12-01T09:30:00' }, now)).toBe(false)
    expect(openToEveryone({ ...open, ends_at: '2026-11-12T11:59:00' }, now)).toBe(false)
    expect(openToEveryone({ ...open, enabled: false }, now)).toBe(false)
    expect(openToEveryone({ ...open, viability: { ...open.viability, viable: false } }, now)).toBe(
      false
    )
  })
})
