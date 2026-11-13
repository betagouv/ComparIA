import type { LLMData } from '$lib/generated/admin'
import { describe, expect, it } from 'vitest'
import { buildCatalogue, clearCriterion, triState } from './filter'

const llm = (id: string, name: string, extra: Partial<LLMData> = {}) =>
  ({ id, name, lab_id: 'l1', status: 'enabled', tags: [], ...extra }) as LLMData

describe('buildCatalogue', () => {
  const catalogue = buildCatalogue({
    llms: [
      llm('2', 'Mistral', { tags: ['legal', 'fr'] }),
      llm('1', 'Gemma', { tags: ['legal'] }),
      llm('3', 'Old one', { status: 'archived', tags: ['retired'] })
    ],
    labs: [{ id: 'l1', name: 'Lab', logo: null, origin_country: 'FR' }],
    licenses: []
  })

  it('offers the models the arena can draw, by name, with their lab', () => {
    expect(catalogue.llmChoices).toEqual([
      { value: '1', label: 'Gemma', hint: 'Lab' },
      { value: '2', label: 'Mistral', hint: 'Lab' }
    ])
  })

  it('suggests every tag set on a model, once', () => {
    expect(catalogue.tags).toEqual(['fr', 'legal', 'retired'])
  })
})

describe('triState', () => {
  it('maps yes, no and either to radio values and back', () => {
    for (const value of [true, false, null]) {
      expect(triState.fromInput(triState.toInput(value))).toBe(value)
    }
    expect(triState.toInput(undefined)).toBe('')
  })
})

describe('clearCriterion', () => {
  it('drops the fields of one criterion and keeps the rest', () => {
    const filter = { params_min: 10, params_max: 60, eu_hostable: true }
    expect(clearCriterion(filter, ['params_min', 'params_max'])).toEqual({ eu_hostable: true })
    expect(filter.params_min).toBe(10)
  })
})
