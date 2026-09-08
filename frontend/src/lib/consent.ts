import { renderInlineMarkdown } from '$components/markdown/inline'
import { api } from '$lib/fastapi-client'
import { m } from '$lib/i18n/messages'
import {
  DEFAULT_INFORMATIONAL_PAGES,
  informationalPageHref,
  isInformationalPageVisible,
  type InformationalPages,
  type InformationalPageSurface
} from '$lib/informational-pages'

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

export type ConsentLink = { label: string; href: string }

// Canonical paths, not the redirects they replaced: a visitor reading what
// they are about to accept should not go through a hop. Every legal
// destination in the app is named here so a page move has one place to land.
export const TERMS_PATH = '/terms'
export const PRIVACY_POLICY_PATH = '/privacy'
export const ACCESSIBILITY_PATH = '/accessibility'
export const ECODESIGN_PATH = '/eco-design'
export const LEGAL_NOTICE_PATH = '/legal'

/** The two documents a visitor accepts, as listed beside the checkbox. */
export function legalLinks(): ConsentLink[] {
  return [
    { label: m['consent.links.terms'](), href: TERMS_PATH },
    { label: m['consent.links.privacy'](), href: PRIVACY_POLICY_PATH }
  ]
}

/** Every public legal page, for the menus that list them all. */
export function legalPageLinks(
  pages: InformationalPages = DEFAULT_INFORMATIONAL_PAGES,
  surface?: InformationalPageSurface
): ConsentLink[] {
  const fixedLinks: ConsentLink[] = [
    { label: m['consent.links.privacy'](), href: PRIVACY_POLICY_PATH },
    { label: m['consent.links.terms'](), href: TERMS_PATH }
  ]
  const informationalLinks = [
    {
      key: 'legal_notice' as const,
      label: m['footer.links.legal'](),
      href: informationalPageHref('legal_notice', pages)
    },
    {
      key: 'accessibility' as const,
      label: m['footer.links.accessibility'](),
      href: informationalPageHref('accessibility', pages)
    },
    {
      key: 'ecodesign' as const,
      label: m['footer.links.rgesn'](),
      href: informationalPageHref('ecodesign', pages)
    }
  ]
  return [
    ...fixedLinks,
    ...informationalLinks.filter(
      (link) => !surface || isInformationalPageVisible(pages[link.key], surface)
    )
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
  const terms = await api.request<TermsResponse>(
    `/settings/legal/terms?locale=${encodeURIComponent(locale)}`
  )
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
