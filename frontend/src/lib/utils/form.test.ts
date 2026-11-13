import { m } from '$lib/i18n/messages'
import { describe, expect, it } from 'vitest'
import { getFormFields, getItemLabel, getSchemaDefaults } from './form'

describe('JSON-schema form fields', () => {
  it('takes labels and help from the generated messages, not the schema', () => {
    const [field] = getFormFields(
      {
        type: 'object',
        properties: { model: { type: 'string', title: 'Schema title', description: 'Schema help' } }
      },
      'prompt_check_upsert'
    )

    expect(field.label).toBe(m['generated.prompt_check_upsert.model.label']())
    expect(field.help).toBe(m['generated.prompt_check_upsert.model.help']())
  })

  it('falls back to the schema when no message exists', () => {
    const [field] = getFormFields(
      { type: 'object', properties: { nope: { type: 'string', title: 'Schema title' } } },
      'prompt_check_upsert'
    )

    expect(field.label).toBe('Schema title')
  })

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

describe('JSON-schema defaults', () => {
  it('starts a new item from the defaults, false and null included', () => {
    const defaults = getSchemaDefaults({
      type: 'object',
      properties: {
        custom_selectable: { type: 'boolean', default: true },
        rate_limited: { type: 'boolean' },
        public: { type: 'boolean', default: false },
        system_prompt: { type: 'string', default: null }
      }
    })

    expect(defaults).toEqual({ custom_selectable: true, public: false, system_prompt: null })
  })
})

describe('JSON-schema lists of text', () => {
  it('types free text values one by one, and keeps fixed choices as checkboxes', () => {
    const fields = getFormFields(
      {
        type: 'object',
        properties: {
          tags: { type: 'array', items: { type: 'string' }, optional: true },
          inputs: { type: 'array', items: { type: 'string', enum: ['text', 'image'] } },
          links: { type: 'array', items: { type: 'string', format: 'uri' } }
        }
      },
      ''
    )

    expect(fields.map((field) => [field.id, field.component])).toEqual([
      ['tags', 'tags'],
      ['inputs', 'checkbox-group'],
      ['links', 'fieldset-list']
    ])
  })
})

describe('JSON-schema choices and nested fields', () => {
  it('shows an enum as radio buttons when asked, stacked when options have help', () => {
    const [plain, helped] = getFormFields(
      {
        type: 'object',
        properties: {
          side: { type: 'string', radio: true, enum: ['a', 'b'] },
          picks: {
            type: 'integer',
            radio: true,
            enum: [{ value: 0, label: 'None', help: 'A blind draw' }] as unknown as number[]
          }
        }
      },
      ''
    )

    expect(plain).toMatchObject({ component: 'radio', inline: true })
    expect(helped).toMatchObject({ component: 'radio', inline: false })
  })

  it('reads text in several languages as one field instead of failing', () => {
    const [field] = getFormFields(
      {
        type: 'object',
        properties: { label: { type: 'object', additionalProperties: { type: 'string' } } }
      },
      ''
    )

    expect(field).toMatchObject({ id: 'label', component: 'translate' })
  })

  it("keeps a referenced field's own label and names nested fields by their path", () => {
    const fields = getFormFields(
      {
        type: 'object',
        properties: { pool: { $ref: '#/$defs/Filter', title: 'Pool' } },
        $defs: {
          Filter: {
            type: 'object',
            title: 'Filter',
            properties: { min: { type: 'number', title: 'Minimum' } }
          }
        }
      },
      ''
    )

    expect(fields[0].label).toBe('Pool')
    expect(getItemLabel(fields, 'pool-min')).toBe('Pool › Minimum')
    expect(getItemLabel(fields, 'unknown')).toBeUndefined()
  })
})
