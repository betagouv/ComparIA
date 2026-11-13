import { describe, expect, it } from 'vitest'
import { parseCohortsParam } from './cohortStore.svelte'

describe('parseCohortsParam', () => {
  it('keeps any well-formed cohort, not only pix', () => {
    expect(parseCohortsParam('acme,pix')).toBe('acme,pix')
  })

  it('drops malformed names and sorts the rest', () => {
    expect(parseCohortsParam('zeta,Bad Name,<x>,alpha-2,zeta')).toBe('alpha-2,zeta')
  })

  it('reads nothing from an empty value', () => {
    expect(parseCohortsParam(null)).toBe('')
  })
})
