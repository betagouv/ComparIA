import { renderInlineMarkdown } from '$components/markdown/inline'
import { api } from '$lib/fastapi-client'

export const PARTICIPATION_STORAGE_KEY = 'comparia:participation-consent:v4'
const PREVIOUS_PARTICIPATION_STORAGE_KEYS = [
  'comparia:participation-consent:v2',
  'comparia:participation-consent:v3'
]
export const LEGACY_TOS_STORAGE_KEY = 'comparia:tos'
export const ANALYTICS_STORAGE_KEY = 'comparia:analytics-consent'

export type ConsentDocument = {
  version: string
  hash: string
  locale: string
  content?: string
  publishedAt?: string
  effectiveAt?: string
  presentation: ConsentPresentation
}

export type ConsentLink = { label: string; href: string }
export const CANONICAL_LEGAL_LINKS: ConsentLink[] = [
  { label: 'Conditions générales d’utilisation', href: '/arene/modalites' },
  { label: 'Politique de confidentialité', href: '/arene/donnees-personnelles' }
]

export type ConsentPresentation = {
  arena: {
    title: string
    introduction: string
    checkboxLabel: string
    links: ConsentLink[]
    buttonLabel: string
  }
  signIn: {
    checkboxLabel: string
    links: ConsentLink[]
  }
}

export type ConsentEvidence = {
  terms_version: string
  terms_hash: string
  accepted_at: string
  locale: string
  legal_information_acknowledged: true
}

export type StoredConsent = ConsentEvidence & {
  schema_version: 4
}

export type AnonymousConsentStatus = {
  terms: null | {
    version: string
    content_hash: string
    locale: string
    accepted_at: string
  }
}

export type ConsentModalState = {
  status: 'loading' | 'accepted' | 'required' | 'error'
  open: boolean
}

export const INITIAL_CONSENT_MODAL_STATE: ConsentModalState = {
  status: 'loading',
  open: false
}

type LegalTermsResponse = {
  version?: string
  terms_version?: string
  content_hash?: string
  terms_hash?: string
  locale?: string
  content?: string
  published_at?: string
  effective_at?: string
  presentation?: {
    arena?: {
      title?: string
      introduction?: string
      checkbox_label?: string
      links?: ConsentLink[]
      button_label?: string | null
    }
    sign_in?: {
      checkbox_label?: string
      links?: ConsentLink[]
    }
  }
}

const DEFAULT_PRESENTATION: ConsentPresentation = {
  arena: {
    title: 'Avant de commencer',
    introduction:
      'Vos messages sont transmis aux modèles d’IA comparés et peuvent être réutilisés pour l’évaluation, la recherche et la production de jeux de données. Ne saisissez aucune donnée sensible ou permettant d’identifier une personne.',
    checkboxLabel: 'J’ai lu et j’accepte les conditions de participation.',
    links: CANONICAL_LEGAL_LINKS,
    buttonLabel: 'Confirmer et envoyer'
  },
  signIn: {
    checkboxLabel: 'J’ai lu et j’accepte les conditions de participation.',
    links: CANONICAL_LEGAL_LINKS
  }
}

function isSha256(value: unknown): value is string {
  return typeof value === 'string' && /^[a-f0-9]{64}$/.test(value)
}

export async function sha256(value: string): Promise<string> {
  const data = new TextEncoder().encode(value)
  const digest = await crypto.subtle.digest('SHA-256', data)
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, '0')).join('')
}

export async function getActiveTerms(locale: string): Promise<ConsentDocument> {
  const terms = await api.request<LegalTermsResponse>(
    `/settings/legal/terms?locale=${encodeURIComponent(locale)}`
  )
  const version = terms.version ?? terms.terms_version
  const suppliedHash = terms.content_hash ?? terms.terms_hash

  if (!version) throw new Error('La version des conditions d’utilisation est indisponible.')

  const hash = isSha256(suppliedHash)
    ? suppliedHash
    : terms.content
      ? await sha256(terms.content)
      : undefined
  if (!hash) throw new Error('L’empreinte des conditions d’utilisation est indisponible.')

  return {
    version,
    hash,
    locale: terms.locale ?? locale,
    content: terms.content,
    publishedAt: terms.published_at,
    effectiveAt: terms.effective_at,
    presentation: {
      arena: {
        title: terms.presentation?.arena?.title ?? DEFAULT_PRESENTATION.arena.title,
        introduction:
          terms.presentation?.arena?.introduction ?? DEFAULT_PRESENTATION.arena.introduction,
        checkboxLabel:
          terms.presentation?.arena?.checkbox_label ?? DEFAULT_PRESENTATION.arena.checkboxLabel,
        links: CANONICAL_LEGAL_LINKS,
        buttonLabel:
          terms.presentation?.arena?.button_label ?? DEFAULT_PRESENTATION.arena.buttonLabel
      },
      signIn: {
        checkboxLabel:
          terms.presentation?.sign_in?.checkbox_label ?? DEFAULT_PRESENTATION.signIn.checkboxLabel,
        links: CANONICAL_LEGAL_LINKS
      }
    }
  }
}

export function buildConsentCheckboxLabel(document: ConsentDocument, login = false): string {
  const presentation = login ? document.presentation.signIn : document.presentation.arena
  return renderInlineMarkdown(presentation.checkboxLabel)
}

export function buildConsentEvidence(
  document: ConsentDocument,
  acceptedAt = new Date().toISOString()
): ConsentEvidence {
  return {
    terms_version: document.version,
    terms_hash: document.hash,
    accepted_at: acceptedAt,
    locale: document.locale,
    legal_information_acknowledged: true
  }
}

export function readStoredConsent(storage: Storage = localStorage): StoredConsent | null {
  try {
    const raw = storage.getItem(PARTICIPATION_STORAGE_KEY)
    if (!raw) return null
    const value = JSON.parse(raw) as Partial<StoredConsent>
    if (
      value.schema_version !== 4 ||
      value.legal_information_acknowledged !== true ||
      !value.terms_version ||
      !isSha256(value.terms_hash) ||
      !value.accepted_at ||
      !value.locale
    ) {
      return null
    }
    return value as StoredConsent
  } catch {
    return null
  }
}

export function storeConsent(evidence: ConsentEvidence, storage: Storage = localStorage): void {
  storage.setItem(
    PARTICIPATION_STORAGE_KEY,
    JSON.stringify({ ...evidence, schema_version: 4 } satisfies StoredConsent)
  )
  storage.removeItem(LEGACY_TOS_STORAGE_KEY)
  for (const key of PREVIOUS_PARTICIPATION_STORAGE_KEYS) storage.removeItem(key)
}

export function hasAcceptedCurrentTerms(
  document: ConsentDocument,
  storage: Storage = localStorage
): boolean {
  const consent = readStoredConsent(storage)
  return consent?.terms_version === document.version && consent.terms_hash === document.hash
}

export async function getConsentStatus(authenticated: boolean): Promise<AnonymousConsentStatus> {
  return api.request<AnonymousConsentStatus>(
    authenticated ? '/auth/consent' : '/auth/consent/anonymous'
  )
}

export function serverHasCurrentAcceptance(
  document: ConsentDocument,
  status: AnonymousConsentStatus
): boolean {
  return (
    status.terms?.version === document.version &&
    status.terms.content_hash === document.hash &&
    status.terms.locale === document.locale
  )
}

export function resolveConsentModalState(
  document: ConsentDocument,
  status: AnonymousConsentStatus
): ConsentModalState {
  return serverHasCurrentAcceptance(document, status)
    ? { status: 'accepted', open: false }
    : { status: 'required', open: false }
}

export function requestConsentModalState(state: ConsentModalState): ConsentModalState {
  return state.status === 'accepted' ? state : { ...state, open: true }
}

export function withdrawLocalConsent(storage: Storage = localStorage): void {
  storage.removeItem(PARTICIPATION_STORAGE_KEY)
  storage.removeItem(LEGACY_TOS_STORAGE_KEY)
}

export type AnalyticsChoice = 'accepted' | 'refused' | null

export function getAnalyticsChoice(storage: Storage = localStorage): AnalyticsChoice {
  const choice = storage.getItem(ANALYTICS_STORAGE_KEY)
  return choice === 'accepted' || choice === 'refused' ? choice : null
}

export function setAnalyticsChoice(
  choice: Exclude<AnalyticsChoice, null>,
  storage: Storage = localStorage
): void {
  storage.setItem(ANALYTICS_STORAGE_KEY, choice)
  if (typeof window !== 'undefined')
    window.dispatchEvent(new CustomEvent('comparia:analytics-choice'))
}
