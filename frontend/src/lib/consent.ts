import { resolve } from '$app/paths'
import { renderInlineMarkdown } from '$components/markdown'
import { api } from '$lib/fastapi-client'
import { m } from '$lib/i18n/messages'
import type { InternalLinkProps } from '$lib/routing'

export type ConsentPresentation = {
  arena: {
    title: string
    introduction: string
    checkboxLabel: string
    buttonLabel: string | null
  }
  signIn: {
    checkboxLabel: string
  }
}

export type ConsentDocument = {
  version: string
  hash: string
  locale: string
  presentation: ConsentPresentation
}

export type ConsentEvidence = {
  terms_version: string
  terms_hash: string
  accepted_at: string
  locale: string
  legal_information_acknowledged: true
}

export type TermsAcceptance = {
  terms: null | {
    version: string
    content_hash: string
    locale: string
    accepted_at: string
  }
}

export type ConsentSnapshot = {
  document: ConsentDocument
  accepted: boolean
}

type TermsResponse = {
  version: string
  content_hash: string
  locale: string
  presentation: {
    arena: {
      title: string
      introduction: string
      checkbox_label: string
      button_label: string | null
    }
    sign_in: {
      checkbox_label: string
    }
  }
}

// Canonical paths, not the redirects they replaced: a visitor reading what
// they are about to accept should not go through a hop. Every legal
// destination in the app is named here so a page move has one place to land.
export const TERMS_PATH = resolve('/terms')
export const PRIVACY_POLICY_PATH = resolve('/privacy_policy')
export const ACCESSIBILITY_PATH = resolve('/accessibility')
export const ECODESIGN_PATH = resolve('/ecodesign')
export const LEGAL_NOTICE_PATH = resolve('/legal_notice')

/** The two documents a visitor accepts, as listed beside the checkbox. */
export function legalLinks(): ({ label: string } & InternalLinkProps)[] {
  return [
    { label: m['consent.links.terms'](), href: TERMS_PATH },
    { label: m['consent.links.privacy_policy'](), href: PRIVACY_POLICY_PATH }
  ]
}

export function consentCheckboxLabel(document: ConsentDocument, signIn = false): string {
  const presentation = signIn ? document.presentation.signIn : document.presentation.arena
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

export function hasAcceptedDocument(
  document: ConsentDocument,
  acceptance: TermsAcceptance
): boolean {
  return (
    acceptance.terms?.version === document.version &&
    acceptance.terms.content_hash === document.hash &&
    acceptance.terms.locale === document.locale
  )
}

async function fetchSnapshot(locale: string, authenticated: boolean): Promise<ConsentSnapshot> {
  const terms = await api.request<TermsResponse>('/settings/legal/terms', {
    searchParams: { locale }
  })
  const acceptance = await api.request<TermsAcceptance>(
    authenticated ? '/auth/consent' : '/auth/consent/anonymous'
  )
  const document: ConsentDocument = {
    version: terms.version,
    hash: terms.content_hash,
    locale: terms.locale,
    presentation: {
      arena: {
        title: terms.presentation.arena.title,
        introduction: terms.presentation.arena.introduction,
        checkboxLabel: terms.presentation.arena.checkbox_label,
        buttonLabel: terms.presentation.arena.button_label
      },
      signIn: {
        checkboxLabel: terms.presentation.sign_in.checkbox_label
      }
    }
  }
  return { document, accepted: hasAcceptedDocument(document, acceptance) }
}

// Several components ask the same question on one page. Sharing the request
// keeps it to a single pair of calls and lets the browser use the ETag.
let cacheKey: string | undefined
let pending: Promise<ConsentSnapshot> | undefined

export function loadConsent(locale: string, authenticated: boolean): Promise<ConsentSnapshot> {
  const key = `${locale}:${authenticated}`
  if (!pending || cacheKey !== key) {
    cacheKey = key
    pending = fetchSnapshot(locale, authenticated)
  }
  return pending
}

export function reloadConsent(locale: string, authenticated: boolean): Promise<ConsentSnapshot> {
  resetConsent()
  return loadConsent(locale, authenticated)
}

export function resetConsent(): void {
  cacheKey = undefined
  pending = undefined
}

export async function submitConsent(
  document: ConsentDocument,
  authenticated: boolean
): Promise<void> {
  await api.request(authenticated ? '/auth/consent' : '/auth/consent/anonymous', {
    method: 'POST',
    body: JSON.stringify({ consent: buildConsentEvidence(document) })
  })
  if (pending) pending = Promise.resolve({ document, accepted: true })
}
