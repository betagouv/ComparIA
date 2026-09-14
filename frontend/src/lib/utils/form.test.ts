import { describe, expect, it } from 'vitest'
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
})
