import type { DatasetCheckPublic, DatasetCheckTryResult } from '$lib/generated/admin'
import { api, ValidationError } from '$lib/fastapi-client'
import type { JSONSchema } from '$lib/utils/form'
import { render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import DatasetCheck from './DatasetCheck.svelte'

vi.mock('$app/navigation', () => ({
  invalidate: vi.fn(),
  beforeNavigate: vi.fn()
}))

vi.mock('$lib/fastapi-client', () => ({
  api: { request: vi.fn() },
  ValidationError: class extends Error {
    constructor(public errors: unknown[]) {
      super('Error in form')
    }
  }
}))

vi.mock('$lib/helpers/useToast.svelte', () => ({
  useToast: vi.fn()
}))

// What GET /admin/dataset-check/schema returns for DatasetCheckUpsert.
const schema = {
  type: 'object',
  properties: {
    model: {
      type: 'string',
      maxLength: 100,
      default: '',
      title: 'Modèle de décision',
      description:
        "Un modèle de décision d'OpenRouter. Vide, aucune conversation n'est analysée ni publiée.",
      optional: true
    },
    api_key: {
      type: 'string',
      optional: true,
      default: null,
      title: 'Clé API OpenRouter',
      description:
        "Laissée vide, l'analyse utilise la clé de la vérification des messages, puis OPENROUTER_API_KEY."
    },
    description: {
      type: 'string',
      maxLength: 2000,
      default: '',
      title: "Description de l'instance",
      description:
        "Le modèle la lit avec chaque conversation. Dites ce qu'est l'instance et ce qui est publié."
    },
    criteria: {
      type: 'array',
      items: { $ref: '#/$defs/DatasetCheckCriterion' },
      maxItems: 32,
      default: [],
      title: "Critères d'exclusion",
      description: "Une conversation qui atteint le seuil d'un critère n'est pas publiée."
    },
    category_threshold: {
      type: 'number',
      maximum: 1,
      minimum: 0,
      default: 0.5,
      title: 'Seuil des thèmes',
      description: 'Un thème est attribué à partir de ce score. Aucun atteint : « Other ».'
    },
    language_threshold: {
      type: 'number',
      maximum: 1,
      minimum: 0,
      default: 0.5,
      title: 'Seuil des langues',
      description: 'Une langue est attribuée à partir de ce score.'
    }
  },
  title: 'DatasetCheckUpsert',
  $defs: {
    DatasetCheckCriterion: {
      type: 'object',
      properties: {
        key: {
          type: 'string',
          title: 'Identifiant',
          description:
            'Les scores enregistrés sont rangés par identifiant : ne le changez plus une fois le critère en service.'
        },
        label: { type: 'string', minLength: 1, maxLength: 80, title: 'Nom' },
        question: {
          type: 'string',
          minLength: 1,
          maxLength: 500,
          title: 'Question posée au modèle',
          description:
            'Une question fermée sur la conversation (le `message`), à laquelle on répond par oui ou non.'
        },
        yes: { type: 'string', maxLength: 1000, default: '', title: 'Compte comme oui' },
        no: { type: 'string', maxLength: 1000, default: '', title: 'Compte comme non' },
        threshold: { type: 'number', maximum: 1, minimum: 0, title: 'Seuil' },
        reason: {
          enum: ['pii', 'spam'],
          type: 'string',
          default: 'spam',
          title: 'Motif',
          description: "Données personnelles ou spam : le drapeau publié et le motif d'archivage."
        }
      },
      required: ['key', 'label', 'question', 'threshold'],
      title: 'DatasetCheckCriterion'
    }
  }
} as unknown as JSONSchema

const check = (overrides: Partial<DatasetCheckPublic> = {}): DatasetCheckPublic => ({
  model: 'perplexity/pplx-decider-v1.2',
  has_api_key: false,
  description: 'Une arène publique.',
  criteria: [
    {
      key: 'pii',
      label: 'Données personnelles',
      question: 'La conversation contient-elle des données personnelles ?',
      yes: '',
      no: '',
      threshold: 0.3,
      reason: 'pii'
    },
    {
      key: 'spam',
      label: 'Spam',
      question: 'La conversation est-elle du spam ?',
      yes: '',
      no: '',
      threshold: 0.3,
      reason: 'spam'
    }
  ],
  category_threshold: 0.5,
  language_threshold: 0.5,
  no_api_key: false,
  no_model: false,
  updated_at: '2026-10-28T10:00:00',
  ...overrides
})

const renderBlock = (status: DatasetCheckPublic) =>
  render(DatasetCheck, { check: status, schema, models: [] })

const flush = async () => {
  for (let i = 0; i < 4; i++) await Promise.resolve()
}

describe('dataset check block', () => {
  it('warns when no model is set', () => {
    const { container } = renderBlock(check({ model: '', no_model: true }))
    expect(container.textContent).toContain('Aucun modèle de décision')
  })

  it('shows the reason, not an action, on each criterion', () => {
    const { container } = renderBlock(check())
    const rows = container.querySelectorAll('#criteria li summary')
    expect(rows).toHaveLength(2)
    expect(rows[0].textContent).toContain('Données personnelles')
    expect(container.querySelector('[name="criteria-0-action"]')).toBeNull()
    expect(container.querySelector('#criteria-0-reason')).not.toBeNull()
  })

  it('tries a conversation with the unsaved settings and shows the outcome', async () => {
    const result: DatasetCheckTryResult = {
      published: false,
      excluded_by: ['pii'],
      categories: ['Law & Justice'],
      languages: ['fr'],
      scores: { pii: 0.91, spam: 0.02, category_law_justice: 0.8, language_fr: 0.99 },
      latency_ms: 420
    }
    vi.mocked(api.request).mockResolvedValueOnce(result)
    const { container } = renderBlock(check())

    const field = container.querySelector<HTMLTextAreaElement>('#dataset-check-try-text')!
    field.value = '[user]: Jean Dupont, 06 12 34 56 78'
    field.dispatchEvent(new Event('input', { bubbles: true }))
    container.querySelector<HTMLButtonElement>('#dataset-check-try-run')!.click()
    await flush()

    const [url, options] = vi.mocked(api.request).mock.calls.at(-1)!
    expect(url).toBe('/admin/dataset-check/try')
    const body = JSON.parse(options!.body as string)
    expect(body.criteria.map((c: { key: string }) => c.key)).toEqual(['pii', 'spam'])
    expect(body.category_threshold).toBe(0.5)

    const shown = container.querySelector('#dataset-check-try-result')!.textContent
    expect(shown).toContain('Ne serait pas publiée')
    expect(container.querySelector('#dataset-check-try-row-pii')!.textContent).toContain(
      'Seuil atteint'
    )
    expect(shown).toContain('Law & Justice')
    expect(shown).toContain('fr')
  })

  it('refuses to try an empty conversation', async () => {
    vi.mocked(api.request).mockClear()
    const { container } = renderBlock(check())
    container.querySelector<HTMLButtonElement>('#dataset-check-try-run')!.click()
    await flush()
    expect(api.request).not.toHaveBeenCalled()
    expect(container.textContent).toContain('Collez une conversation à analyser.')
  })

  it('opens a saved criterion on the field the server refused', async () => {
    vi.mocked(api.request).mockRejectedValueOnce(
      new ValidationError([{ loc: ['body', 'criteria', 0, 'question'], msg: 'Trop longue' }])
    )
    const { container } = renderBlock(check())
    const row = container.querySelector<HTMLDetailsElement>('#criteria-0 details')!
    expect(row.open).toBe(false)

    container.querySelector<HTMLFormElement>('#dataset-check-form')!.requestSubmit()
    await flush()

    expect(row.open).toBe(true)
    const group = container.querySelector('#criteria-0-question')!.closest('.fr-input-group')!
    expect(group.textContent).toContain('Trop longue')
    expect(container.querySelector('#criteria-1 details')!.hasAttribute('open')).toBe(false)
  })
})
