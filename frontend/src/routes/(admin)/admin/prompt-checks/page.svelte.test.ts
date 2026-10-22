import type { PromptCheckCriterion, PromptCheckStatus } from '$lib/generated/admin'
import type { JSONSchema } from '$lib/utils/form'
import { render } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import type { PageProps } from './$types'
import Page from './+page.svelte'
import type { PromptCheckStats, PromptCheckTry } from './types'

vi.mock('$app/navigation', () => ({
  invalidate: vi.fn(),
  beforeNavigate: vi.fn()
}))

vi.mock('$lib/fastapi-client', () => ({
  api: { request: vi.fn() },
  ValidationError: class extends Error {}
}))

vi.mock('$lib/helpers/useToast.svelte', () => ({
  useToast: vi.fn()
}))

// What GET /admin/prompt-check/schema returns for PromptCheckUpsert.
const schema = {
  type: 'object',
  properties: {
    enabled: { type: 'boolean', default: true, title: 'Vérification des messages' },
    required: {
      type: 'boolean',
      default: true,
      title: 'Vérification obligatoire',
      description:
        "Quand la vérification ne répond pas (délai dépassé, OpenRouter saturé, clé refusée), le message est refusé. Désactivée, il passe sans être vérifié. Dans les deux cas, après plusieurs échecs d'OpenRouter d'affilée, les messages passent sans vérification une minute à la fois."
    },
    model: {
      type: 'string',
      minLength: 1,
      maxLength: 100,
      default: 'perplexity/pplx-decider-v1.2-20261016',
      title: 'Modèle de décision',
      description: "Un modèle de décision d'OpenRouter."
    },
    api_key: {
      type: 'string',
      optional: true,
      default: null,
      title: 'Clé API OpenRouter',
      description: 'Laissée vide, la vérification utilise OPENROUTER_API_KEY.'
    },
    description: {
      type: 'string',
      maxLength: 2000,
      default:
        "compar:IA est un service public gratuit de l'État français. Chacun peut discuter avec deux modèles d'IA anonymes et voter pour la meilleure réponse. Toute question ou tâche sincère est la bienvenue, y compris sur la santé, le droit, l'argent, le commerce ou la création, et les questions sur les modèles eux-mêmes.",
      title: "Description de l'instance",
      description:
        "Le modèle la lit avec chaque message. Dites ce qui est bienvenu ici, pour qu'une question de santé ne passe pas pour suspecte sur une arène santé."
    },
    criteria: {
      type: 'array',
      items: { $ref: '#/$defs/PromptCheckCriterion' },
      default: [],
      title: 'Critères'
    },
    conversations_per_ip_per_hour: {
      type: 'integer',
      maximum: 10000,
      minimum: 0,
      optional: true,
      default: null,
      title: 'Conversations par IP et par heure',
      description:
        "Sur une heure glissante, même quand la vérification est désactivée. Partagée par tous ceux qui sortent par la même IP (une école, un ministère) ; les cohortes partenaires (Pix) n'y sont pas soumises. 0 désactive la limite, vide revient à la valeur par défaut de l'instance."
    },
    conversations_same_models_per_ip_per_hour: {
      type: 'integer',
      maximum: 10000,
      minimum: 0,
      optional: true,
      default: null,
      title: 'Conversations par IP et par heure avec les mêmes modèles',
      description:
        "La même limite, pour une même paire de modèles. 0 la désactive, vide revient à la valeur par défaut de l'instance."
    }
  },
  title: 'PromptCheckUpsert',
  $defs: {
    PromptCheckCriterion: {
      type: 'object',
      properties: {
        key: {
          type: 'string',
          title: 'Identifiant',
          description:
            'Les statistiques sont comptées par identifiant : ne le changez plus une fois le critère en service.'
        },
        label: { type: 'string', minLength: 1, maxLength: 80, title: 'Nom' },
        question: {
          type: 'string',
          minLength: 1,
          maxLength: 500,
          title: 'Question posée au modèle',
          description: 'Une question fermée sur le `message`, à laquelle on répond par oui ou non.'
        },
        yes: { type: 'string', maxLength: 1000, default: '', title: 'Compte comme oui' },
        no: { type: 'string', maxLength: 1000, default: '', title: 'Compte comme non' },
        threshold: { type: 'number', maximum: 1, minimum: 0, title: 'Seuil' },
        action: { enum: ['off', 'log', 'warn', 'block'], type: 'string', title: 'Action' },
        message: {
          enum: ['generic', 'self_harm', 'pii'],
          type: 'string',
          default: 'generic',
          title: 'Message affiché'
        }
      },
      required: ['key', 'label', 'question', 'threshold', 'action'],
      title: 'PromptCheckCriterion'
    }
  }
} as unknown as JSONSchema

const criterion = (
  key: string,
  label: string,
  threshold: number,
  action: PromptCheckCriterion['action'],
  message: PromptCheckCriterion['message'] = 'generic'
): PromptCheckCriterion => ({
  key,
  label,
  question: `Le \`message\` relève-t-il de ${label} ?`,
  yes: '',
  no: '',
  threshold,
  action,
  message
})

// Indexes 0, 1 and 2 in the field ids.
const criteria = [
  criterion('sexual', 'Contenu sexuel', 0.3, 'log'),
  criterion('pii', 'Données personnelles', 0.5, 'warn', 'pii'),
  criterion('criminal', 'Activités criminelles', 0.5, 'log')
]

const check = (overrides: Partial<PromptCheckStatus> = {}): PromptCheckStatus => ({
  enabled: true,
  required: true,
  has_api_key: false,
  model: 'perplexity/pplx-decider-v1.2-20261016',
  description: 'Une arène publique.',
  criteria: criteria.map((c) => ({ ...c })),
  conversations_per_ip_per_hour: null,
  conversations_same_models_per_ip_per_hour: 0,
  default_conversations_per_ip_per_hour: 20,
  default_conversations_same_models_per_ip_per_hour: 5,
  updated_at: '2026-07-01T10:00:00',
  consecutive_failures: 0,
  key_rejected: false,
  out_of_credits: false,
  no_api_key: false,
  healthy: true,
  warnings_shown: 0,
  ...overrides
})

const tried = (overrides: Partial<PromptCheckTry> = {}): PromptCheckTry => ({
  decision: 'warned',
  scores: { sexual: 0.01, pii: 0.99, criminal: 0.41 },
  triggered: { pii: 'warn' },
  message: 'pii',
  latency_ms: 210,
  error: null,
  ...overrides
})

const stats = (overrides: Partial<PromptCheckStats> = {}): PromptCheckStats => ({
  period: 'all',
  bucket: 'month',
  historical_total: 1234,
  total: 1234,
  by_decision: { pass: 1000, logged: 200, warned: 30, blocked: 4, error: 0 },
  by_category: { pii: { warned: 22 }, criminal: { blocked: 8 } },
  timeline: [
    {
      date: '2026-07-01',
      by_decision: { pass: 1000, logged: 200, warned: 30, blocked: 4, error: 0 }
    }
  ],
  ...overrides
})

const renderPage = (status: PromptCheckStatus, pageStats: PromptCheckStats | null = null) =>
  render(Page, {
    data: {
      check: status,
      schema,
      stats: pageStats,
      models: [{ id: 'perplexity/pplx-decider-flash-v1.2', name: 'Decider Flash V1.2' }]
    } as unknown as PageProps['data'],
    params: {} as PageProps['params']
  })

const flush = async () => {
  for (let i = 0; i < 4; i++) await Promise.resolve()
}

const type = (container: HTMLElement, selector: string, value: string) => {
  const field = container.querySelector<HTMLInputElement | HTMLTextAreaElement>(selector)!
  field.value = value
  field.dispatchEvent(new Event('input', { bubbles: true }))
  return field
}

const pick = (container: HTMLElement, selector: string) => {
  const radio = container.querySelector<HTMLInputElement>(selector)!
  radio.checked = true
  radio.dispatchEvent(new Event('change', { bubbles: true }))
}

const save = async (container: HTMLElement) => {
  container
    .querySelector('#prompt-check-form')!
    .dispatchEvent(new Event('submit', { bubbles: true }))
  await flush()
}

const mockApi = async (value: unknown) => {
  const { api } = await import('$lib/fastapi-client')
  vi.mocked(api.request).mockReset()
  vi.mocked(api.request).mockResolvedValue(value)
  return api
}

const sentBody = async (call = 0) => {
  const { api } = await import('$lib/fastapi-client')
  return JSON.parse(vi.mocked(api.request).mock.calls[call][1]!.body as string)
}

describe('admin prompt check page', () => {
  it('draws the settings from the schema, labels included', () => {
    const { getByText, container } = renderPage(check())

    expect(getByText('Modèle de décision')).toBeInTheDocument()
    expect(getByText('Clé API OpenRouter')).toBeInTheDocument()
    expect(getByText("Description de l'instance")).toBeInTheDocument()
    expect(container.querySelector<HTMLInputElement>('#model')?.value).toBe(
      'perplexity/pplx-decider-v1.2-20261016'
    )
    expect(container.querySelector<HTMLTextAreaElement>('#description')?.value).toBe(
      'Une arène publique.'
    )
  })

  it('saves the whole form at once, without what the API only reports', async () => {
    const api = await mockApi(check())

    const { container } = renderPage(check())
    type(container, '#criteria-1-threshold', '0.65')
    pick(container, '#criteria-0-action-block')
    type(container, '#description', 'Une arène santé.')
    await save(container)

    expect(api.request).toHaveBeenCalledWith(
      '/admin/prompt-check',
      expect.objectContaining({ method: 'put' })
    )
    const body = await sentBody()
    expect(Object.keys(body).sort()).toEqual([
      'api_key',
      'conversations_per_ip_per_hour',
      'conversations_same_models_per_ip_per_hour',
      'criteria',
      'description',
      'enabled',
      'model',
      'required'
    ])
    // An empty key field keeps the stored key.
    expect(body.api_key).toBeFalsy()
    expect(body.description).toBe('Une arène santé.')
    expect(body.criteria[1]).toEqual({ ...criteria[1], threshold: 0.65 })
    expect(body.criteria[0]).toEqual({ ...criteria[0], action: 'block' })
  })

  it('sends a typed key, and leaves it out otherwise', async () => {
    await mockApi(check({ has_api_key: true }))

    const { container } = renderPage(check({ has_api_key: true }))
    expect(container.querySelector<HTMLInputElement>('#api_key')?.type).toBe('password')
    type(container, '#api_key', 'nouvelle-cle')
    await save(container)

    expect((await sentBody()).api_key).toBe('nouvelle-cle')
  })

  it('removes a stored key after a confirmation', async () => {
    const api = await mockApi(check())

    const { container } = renderPage(check({ has_api_key: true }))
    container.querySelector<HTMLButtonElement>('#prompt-check-api-key-remove')!.click()
    await flush()
    expect(api.request).not.toHaveBeenCalled()
    container.querySelector<HTMLButtonElement>('#prompt-check-api-key-remove-confirm')!.click()
    await flush()

    expect(api.request).toHaveBeenCalledWith('/admin/prompt-check/api-key', { method: 'delete' })
  })

  it('offers no removal when no key is stored', () => {
    const { container } = renderPage(check())

    expect(container.querySelector('#prompt-check-api-key-remove')).not.toBeInTheDocument()
  })

  it('offers the listed decision models without limiting the field to them', () => {
    const { container } = renderPage(check())

    expect(container.querySelector('#model')?.getAttribute('list')).toBe(
      'prompt-check-model-options'
    )
    const options = [...container.querySelectorAll('#prompt-check-model-options option')]
    expect(options.map((option) => option.getAttribute('value'))).toEqual([
      'perplexity/pplx-decider-flash-v1.2'
    ])
  })

  it('folds saved criteria and shows their action and threshold', () => {
    const { container } = renderPage(check())

    const row = container.querySelector('#criteria-1')!
    expect(row.querySelector('details')?.open).toBe(false)
    expect(row.querySelector('summary')?.textContent?.replace(/\s+/g, ' ')).toContain(
      'Données personnelles Prévenir Seuil 0,5'
    )
  })

  it('offers the four actions per criterion and preselects the stored one', () => {
    const { container } = renderPage(check())

    const labels = [...container.querySelectorAll('#criteria-0 .action-pills label')]
      .map((label) => label.textContent?.trim())
      .filter(Boolean)
    expect(labels).toEqual(['Ignorer', 'Surveiller', 'Prévenir', 'Refuser'])

    const checked = (index: number, action: string) =>
      container.querySelector<HTMLInputElement>(`#criteria-${index}-action-${action}`)?.checked
    expect(checked(0, 'log')).toBe(true)
    expect(checked(0, 'block')).toBe(false)
    expect(checked(1, 'warn')).toBe(true)
  })

  it('keeps the key of a saved criterion out of reach', () => {
    const { container } = renderPage(check())

    expect(container.querySelector<HTMLInputElement>('#criteria-0-key')?.disabled).toBe(true)
  })

  it('adds a criterion that takes its key from its name', async () => {
    await mockApi(check())

    const { container } = renderPage(check())
    container.querySelector<HTMLButtonElement>('#prompt-check-criteria-add')!.click()
    await flush()
    expect(container.querySelector('#criteria-3 details')?.hasAttribute('open')).toBe(true)
    type(container, '#criteria-3-label', 'Hors sujet : pubs')
    type(container, '#criteria-3-question', 'Le `message` est-il une publicité ?')
    type(container, '#criteria-3-yes', 'Liens, promotions')
    await save(container)

    expect((await sentBody()).criteria[3]).toEqual({
      key: 'hors_sujet_pubs',
      label: 'Hors sujet : pubs',
      question: 'Le `message` est-il une publicité ?',
      yes: 'Liens, promotions',
      no: '',
      threshold: 0.5,
      action: 'log',
      message: 'generic'
    })
  })

  it('opens a folded criterion the server refused and shows why on its field', async () => {
    const { api, ValidationError } = await import('$lib/fastapi-client')
    vi.mocked(api.request).mockReset()
    vi.mocked(api.request).mockRejectedValue(
      Object.assign(new ValidationError('invalid'), {
        errors: [{ loc: ['body', 'criteria', 1, 'question'], msg: 'Too long' }]
      })
    )

    const { container } = renderPage(check())
    expect(container.querySelector('#criteria-1 details')?.hasAttribute('open')).toBe(false)
    await save(container)

    expect(container.querySelector('#criteria-1 details')?.hasAttribute('open')).toBe(true)
    expect(container.querySelector('#criteria-1-question-messages')?.textContent).toContain(
      'Too long'
    )
  })

  it('removes a criterion', async () => {
    await mockApi(check())

    const { container } = renderPage(check())
    container.querySelector<HTMLButtonElement>('#criteria-0-remove')!.click()
    await flush()
    await save(container)

    const sent = (await sentBody()).criteria.map((c: PromptCheckCriterion) => c.key)
    expect(sent).toEqual(['pii', 'criminal'])
  })

  it('explains what the four actions do, warning included', () => {
    const { getByText } = renderPage(check())

    expect(getByText('Ce que fait chaque action')).toBeInTheDocument()
    expect(getByText(/La personne peut envoyer quand même/)).toBeInTheDocument()
  })

  it('says so when the check has stopped working, and stays quiet when it has not', () => {
    const { getByText, unmount } = renderPage(check({ healthy: false, consecutive_failures: 7 }))

    expect(getByText('La vérification ne répond plus')).toBeInTheDocument()
    expect(getByText('7 échecs consécutifs')).toBeInTheDocument()
    unmount()

    const healthy = renderPage(check())
    expect(healthy.queryByText('La vérification ne répond plus')).not.toBeInTheDocument()
  })

  it('says messages go through while a check that is not required fails', () => {
    const { getByText } = renderPage(
      check({ required: false, healthy: false, consecutive_failures: 7 })
    )

    expect(getByText(/les messages passent sans être vérifiés/)).toBeInTheDocument()
  })

  it('shows the default an empty conversation cap falls back to', async () => {
    await mockApi(check())

    const { container } = renderPage(check())
    const perIp = container.querySelector<HTMLInputElement>('#conversations_per_ip_per_hour')!
    expect(perIp.value).toBe('')
    expect(perIp.placeholder).toBe('20')
    // Zero is a cap turned off, not an empty field.
    expect(
      container.querySelector<HTMLInputElement>('#conversations_same_models_per_ip_per_hour')?.value
    ).toBe('0')

    await save(container)
    const body = await sentBody()
    expect(body.conversations_per_ip_per_hour).toBeNull()
    expect(body.conversations_same_models_per_ip_per_hour).toBe(0)
  })

  it('offers the switch that makes the check required', () => {
    const { getByText, container } = renderPage(check())

    expect(getByText('Vérification obligatoire')).toBeInTheDocument()
    expect(container.querySelector<HTMLInputElement>('#required')?.checked).toBe(true)
  })

  it('says the credits ran out instead of the generic failure', () => {
    const { getByText, queryByText } = renderPage(
      check({ healthy: false, out_of_credits: true, consecutive_failures: 0 })
    )

    expect(getByText("OpenRouter n'a plus de crédits pour cette clé")).toBeInTheDocument()
    expect(queryByText('La vérification ne répond plus')).not.toBeInTheDocument()
  })

  it('says the check does not run when there is no key at all', () => {
    const { getByText } = renderPage(check({ no_api_key: true }))

    expect(getByText('Aucune clé API')).toBeInTheDocument()
  })

  it('says nothing about a missing key while the check is off', () => {
    const { queryByText } = renderPage(check({ enabled: false, no_api_key: true }))

    expect(queryByText('Aucune clé API')).not.toBeInTheDocument()
  })

  it('names a rejected key instead of the generic failure', () => {
    const { getByText, queryByText } = renderPage(
      check({ healthy: false, key_rejected: true, consecutive_failures: 0 })
    )

    expect(getByText('OpenRouter refuse la clé')).toBeInTheDocument()
    expect(queryByText('La vérification ne répond plus')).not.toBeInTheDocument()
  })

  it('runs the bench against the on-screen settings, not the stored ones', async () => {
    const api = await mockApi(tried())

    const { container } = renderPage(check())
    type(container, '#criteria-1-threshold', '0.65')
    type(container, '#description', 'Une arène santé.')
    type(container, '#prompt-check-bench-text', 'un message à vérifier')
    container.querySelector<HTMLButtonElement>('#prompt-check-bench-run')!.click()
    await flush()

    expect(api.request).toHaveBeenCalledWith(
      '/admin/prompt-check/try',
      expect.objectContaining({ method: 'POST' })
    )
    const body = await sentBody()
    expect(body.text).toBe('un message à vérifier')
    expect(body.model).toBe('perplexity/pplx-decider-v1.2-20261016')
    expect(body.description).toBe('Une arène santé.')
    expect(body.criteria[1]).toEqual({ ...criteria[1], threshold: 0.65 })
  })

  it('shows every criterion score, whether it fired or not', async () => {
    await mockApi(tried())

    const { container, getByText } = renderPage(check())
    type(container, '#prompt-check-bench-text', 'appelle Jean Dupont au 06 12 34 56 78')
    container.querySelector<HTMLButtonElement>('#prompt-check-bench-run')!.click()
    await flush()

    expect(getByText('Prévenu')).toBeInTheDocument()
    expect(getByText('Réponse en 210 ms')).toBeInTheDocument()
    expect(container.querySelector('#prompt-check-bench-message')?.textContent?.trim()).toBe(
      'Votre message semble contenir des données personnelles. Les messages envoyés peuvent être publiés dans le jeu de données ouvert.'
    )

    const fired = container.querySelector('#prompt-check-bench-row-pii')!
    expect(fired.textContent).toContain('Données personnelles')
    expect(fired.textContent).toContain('0,990')
    expect(fired.textContent).toContain('Déclenché')

    const quiet = container.querySelector('#prompt-check-bench-row-criminal')!
    expect(quiet.textContent).toContain('0,410')
    expect(quiet.textContent).toContain('Sous le seuil')
  })

  it('renders historical activity and period-aligned charts', () => {
    const { container, getByText } = renderPage(check(), stats({ total: 5 }))

    expect(container.querySelector('#prompt-check-stats-total')?.textContent?.trim()).toBe('5')
    expect(getByText('Détections dans le temps')).toBeInTheDocument()

    const blocked = container.querySelector('#prompt-check-stats-decision-blocked')?.textContent
    expect(blocked).toContain('Refusés')
    expect(blocked).toContain('4')

    const pii = container.querySelector('#prompt-check-stats-category-pii')?.textContent
    expect(pii).toContain('Données personnelles')
    expect(pii).toContain('22')
  })

  it('reloads all period-aligned indicators when the period changes', async () => {
    const api = await mockApi(stats({ period: '30d', bucket: 'day' }))
    const { container } = renderPage(check(), stats())
    const select = container.querySelector<HTMLSelectElement>('#prompt-check-stats-period')!
    select.value = '30d'
    select.dispatchEvent(new Event('change', { bubbles: true }))
    await flush()

    expect(api.request).toHaveBeenCalledWith(
      '/admin/prompt-check/stats',
      expect.objectContaining({ searchParams: { period: '30d' } })
    )
  })

  it('stays readable when the counts are missing', () => {
    const { getByText } = renderPage(check())

    expect(getByText('Les compteurs ne sont pas disponibles pour le moment.')).toBeInTheDocument()
  })
})
