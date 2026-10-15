import { describe, expect, it } from 'vitest'
import { overwriteGetLocale } from '$lib/i18n/runtime'
import { getFormFields } from './form'

describe('JSON-schema form fields', () => {
  it('renders calendar dates without a time control', () => {
    const fields = getFormFields(
      {
        type: 'object',
        properties: {
          release_date: { type: 'string', format: 'date' },
          knowledge_cutoff: { type: 'string', format: 'date', optional: true }
        },
        required: ['release_date']
      },
      ''
    )

    expect(fields).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ id: 'release_date', type: 'date', required: true }),
        expect.objectContaining({ id: 'knowledge_cutoff', type: 'date', required: false })
      ])
    )
  })

  it('gives number inputs the bounds and the step of the schema', () => {
    const fields = getFormFields(
      {
        type: 'object',
        properties: {
          score: { type: 'number', minimum: 1, maximum: 100, step: 1 },
          params: { type: 'number' },
          count: { type: 'integer', minimum: 0 }
        }
      },
      ''
    )

    expect(fields).toEqual([
      expect.objectContaining({ id: 'score', min: 1, max: 100, step: '1' }),
      expect.objectContaining({ id: 'params', min: undefined, step: '0.0001' }),
      expect.objectContaining({ id: 'count', min: 0, max: undefined, step: '1' })
    ])
  })

  it('does not make generated hidden or disabled inputs browser-required', () => {
    const fields = getFormFields(
      {
        type: 'object',
        properties: {
          id: { type: 'string', hidden: true },
          created_at: { type: 'string', disabled: true }
        },
        required: ['id', 'created_at']
      },
      ''
    )

    expect(fields).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ id: 'id', required: false }),
        expect.objectContaining({ id: 'created_at', required: false })
      ])
    )
  })

  it('labels a field from the translations of the locale in force', () => {
    const schema = {
      type: 'object' as const,
      properties: { daily_usd_cap: { type: 'number' as const, title: 'Schema title' } }
    }
    overwriteGetLocale(() => 'en')
    const [en] = getFormFields(schema, 'llm_upsert')
    overwriteGetLocale(() => 'da')
    const [da] = getFormFields(schema, 'llm_upsert')
    overwriteGetLocale(() => 'fr')

    expect([en.label, da.label]).toEqual(['Daily cap (USD)', 'Dagligt loft (USD)'])
  })
})
