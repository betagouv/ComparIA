import { describe, expect, it } from 'vitest'
import {
  fallbackModes,
  keepAllowedTools,
  keepPickable,
  pickCurrentMode,
  type SelectionMode
} from './selectionModes.svelte'

function mode(key: string, extra: Partial<SelectionMode> = {}): SelectionMode {
  return {
    key,
    label: key,
    short_label: key,
    description: null,
    icon: 'i-ri-dice-line',
    is_default: false,
    visitor_picks: 0,
    tools_policy: 'visitor',
    tool_keys: ['web_search', 'datagouv'],
    llm_ids: null,
    ...extra
  }
}

const modes = [mode('first'), mode('default', { is_default: true }), mode('other')]

describe('pickCurrentMode', () => {
  it('keeps the remembered mode while it is on offer', () => {
    expect(pickCurrentMode(modes, 'other').key).toBe('other')
  })

  it('falls back to the default mode once the remembered one is gone', () => {
    expect(pickCurrentMode(modes, 'deleted-mode').key).toBe('default')
    expect(pickCurrentMode(modes, '').key).toBe('default')
  })

  it('takes the first mode when none is marked default', () => {
    expect(pickCurrentMode([mode('a'), mode('b')], 'gone').key).toBe('a')
  })
})

describe('keepPickable', () => {
  const pool = mode('pool', { visitor_picks: 1, llm_ids: ['a', 'b'] })

  it('drops models outside the pool and past the pick limit', () => {
    expect(keepPickable(['c', 'b', 'a'], pool)).toEqual(['b'])
  })

  it('keeps a second pick only from the other pool', () => {
    const split = mode('split', {
      visitor_picks: 2,
      llm_ids: ['a1', 'a2', 'b1'],
      llm_ids_a: ['a1', 'a2'],
      llm_ids_b: ['b1']
    })
    expect(keepPickable(['a1', 'a2'], split)).toEqual(['a1'])
    expect(keepPickable(['b1', 'a2'], split)).toEqual(['b1', 'a2'])
  })

  it('keeps nothing in a blind mode', () => {
    expect(keepPickable(['a'], mode('blind'))).toEqual([])
  })
})

describe('keepAllowedTools', () => {
  it('keeps only the tools the mode offers', () => {
    const narrowed = mode('narrow', { tool_keys: ['datagouv'] })
    expect(keepAllowedTools(['web_search', 'datagouv'], narrowed)).toEqual(['datagouv'])
  })

  it('drops every tool in a mode without tools', () => {
    expect(keepAllowedTools(['web_search'], mode('none', { tools_policy: 'none' }))).toEqual([])
  })

  it('uses the forced tools whatever was picked', () => {
    const forced = mode('forced', { tools_policy: 'forced', tool_keys: ['web_search'] })
    expect(keepAllowedTools([], forced)).toEqual(['web_search'])
  })
})

describe('fallbackModes', () => {
  it('is a single blind default draw offering the given tools', () => {
    const [fallback, ...rest] = fallbackModes(['web_search'])
    expect(rest).toHaveLength(0)
    expect(fallback).toMatchObject({
      is_default: true,
      visitor_picks: 0,
      tools_policy: 'visitor',
      tool_keys: ['web_search'],
      llm_ids: null
    })
  })
})
