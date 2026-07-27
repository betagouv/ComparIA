import { isRedirect } from '@sveltejs/kit'
import { load as donneesPersonnelles } from '../routes/(pages)/(general)/donnees-personnelles/+page.server'
import { load as modalites } from '../routes/(pages)/(general)/modalites/+page.server'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  buildConsentEvidence,
  consentCheckboxLabel,
  hasAcceptedDocument,
  legalLinks,
  loadConsent,
  reloadConsent,
  resetConsent,
  submitConsent,
  type ConsentDocument
} from './consent'
import { api } from './fastapi-client'

const document: ConsentDocument = {
  version: '2026-07-20',
  hash: 'a'.repeat(64),
  locale: 'fr',
  presentation: {
    arena: {
      title: 'Avant de commencer',
      introduction: 'Texte configuré',
      checkboxLabel: '**Je confirme** ma participation',
      buttonLabel: 'Confirmer et envoyer'
    },
    signIn: {
      checkboxLabel: 'Je confirme avant de me connecter'
    }
  }
}

const termsResponse = {
  version: document.version,
  content_hash: document.hash,
  locale: document.locale,
  presentation: {
    arena: {
      title: document.presentation.arena.title,
      introduction: document.presentation.arena.introduction,
      checkbox_label: document.presentation.arena.checkboxLabel,
      button_label: document.presentation.arena.buttonLabel
    },
    sign_in: { checkbox_label: document.presentation.signIn.checkboxLabel }
  }
}

const acceptance = {
  version: document.version,
  content_hash: document.hash,
  locale: document.locale,
  accepted_at: '2026-07-20T10:00:00.000Z'
}

function redirectTarget(load: () => void): string {
  try {
    load()
  } catch (error) {
    if (isRedirect(error)) return error.location
    throw error
  }
  throw new Error('the load did not redirect')
}

describe('consent', () => {
  beforeEach(() => {
    resetConsent()
    vi.restoreAllMocks()
  })

  it('sends the exact version and hash the visitor was shown', () => {
    expect(buildConsentEvidence(document, '2026-07-20T10:00:00.000Z')).toEqual({
      terms_version: document.version,
      terms_hash: document.hash,
      accepted_at: '2026-07-20T10:00:00.000Z',
      locale: document.locale,
      legal_information_acknowledged: true
    })
  })

  it('links to the published pages, not to the paths that redirect', () => {
    expect(legalLinks().map((link) => link.href)).toEqual([
      '/arene/modalites',
      '/arene/donnees-personnelles'
    ])
    // Tied to where the legacy routes send visitors, so moving a document
    // without moving these links turns red here rather than adding a hop.
    expect(legalLinks().map((link) => link.href)).toEqual(
      [modalites, donneesPersonnelles].map(redirectTarget)
    )
  })

  it('renders the checkbox label of the page that asks', () => {
    expect(consentCheckboxLabel(document)).toContain('<strong>Je confirme</strong>')
    expect(consentCheckboxLabel(document, true)).toBe('Je confirme avant de me connecter')
  })

  it('requires the recorded acceptance to match the document exactly', () => {
    expect(hasAcceptedDocument(document, { terms: acceptance })).toBe(true)
    expect(
      hasAcceptedDocument(document, { terms: { ...acceptance, content_hash: 'b'.repeat(64) } })
    ).toBe(false)
    expect(hasAcceptedDocument(document, { terms: null })).toBe(false)
  })

  it('fetches the document and the acceptance once for the whole page', async () => {
    const request = vi.spyOn(api, 'request').mockImplementation((path: string) => {
      if (path.startsWith('/settings/legal/terms')) return Promise.resolve(termsResponse) as never
      return Promise.resolve({ terms: null }) as never
    })

    const [first, second] = await Promise.all([loadConsent('fr', false), loadConsent('fr', false)])

    expect(request).toHaveBeenCalledTimes(2)
    expect(request.mock.calls.map(([path]) => path)).toEqual([
      '/settings/legal/terms?locale=fr',
      '/auth/consent/anonymous'
    ])
    expect(first).toBe(second)
    expect(first.accepted).toBe(false)
    expect(first.document).toEqual(document)
  })

  it('asks again after a failure so the user can retry', async () => {
    let fail = true
    const request = vi.spyOn(api, 'request').mockImplementation((path: string) => {
      if (fail) return Promise.reject(new Error('offline')) as never
      if (path.startsWith('/settings/legal/terms')) return Promise.resolve(termsResponse) as never
      return Promise.resolve({ terms: acceptance }) as never
    })

    await expect(loadConsent('fr', false)).rejects.toThrow('offline')
    await expect(loadConsent('fr', false)).rejects.toThrow('offline')
    expect(request).toHaveBeenCalledTimes(1)

    fail = false
    await expect(reloadConsent('fr', false)).resolves.toMatchObject({ accepted: true })
  })

  it('does not ask the server again after recording an acceptance', async () => {
    const request = vi.spyOn(api, 'request').mockImplementation((path: string) => {
      if (path.startsWith('/settings/legal/terms')) return Promise.resolve(termsResponse) as never
      return Promise.resolve({ terms: null }) as never
    })

    await loadConsent('fr', false)
    await submitConsent(document, false)

    expect(request).toHaveBeenLastCalledWith(
      '/auth/consent/anonymous',
      expect.objectContaining({ method: 'POST' })
    )
    await expect(loadConsent('fr', false)).resolves.toEqual({ document, accepted: true })
    expect(request).toHaveBeenCalledTimes(3)
  })
})
