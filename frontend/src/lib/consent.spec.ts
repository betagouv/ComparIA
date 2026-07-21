import { describe, expect, it } from 'vitest'
import {
  buildConsentEvidence,
  hasAcceptedCurrentTerms,
  INITIAL_CONSENT_MODAL_STATE,
  readStoredConsent,
  requestConsentModalState,
  resolveConsentModalState,
  serverHasCurrentAcceptance,
  storeConsent,
  withdrawLocalConsent,
  type ConsentDocument
} from './consent'

function memoryStorage(): Storage {
  const values = new Map<string, string>()
  return {
    get length() {
      return values.size
    },
    clear: () => values.clear(),
    getItem: (key) => values.get(key) ?? null,
    key: (index) => [...values.keys()][index] ?? null,
    removeItem: (key) => values.delete(key),
    setItem: (key, value) => values.set(key, value)
  }
}

const terms: ConsentDocument = {
  version: '2026-07-20',
  hash: 'a'.repeat(64),
  locale: 'fr',
  presentation: {
    arena: {
      title: 'Avant de commencer',
      introduction: 'Texte configuré',
      checkboxLabel: 'Je confirme',
      buttonLabel: 'Confirmer et envoyer'
    },
    signIn: {
      checkboxLabel: 'Je confirme pour me connecter'
    }
  }
}

describe('consent evidence', () => {
  it('stores acceptance against the exact terms version and hash', () => {
    const storage = memoryStorage()
    const evidence = buildConsentEvidence(terms, '2026-07-20T10:00:00.000Z')

    storeConsent(evidence, storage)

    expect(readStoredConsent(storage)).toMatchObject(evidence)
    expect(hasAcceptedCurrentTerms(terms, storage)).toBe(true)
    expect(hasAcceptedCurrentTerms({ ...terms, version: '2026-08-01' }, storage)).toBe(false)
  })

  it('withdraws local participation evidence', () => {
    const storage = memoryStorage()
    storeConsent(buildConsentEvidence(terms), storage)
    withdrawLocalConsent(storage)
    expect(readStoredConsent(storage)).toBeNull()
  })

  it('requires the server acceptance to match the active document exactly', () => {
    expect(
      serverHasCurrentAcceptance(terms, {
        terms: {
          version: terms.version,
          content_hash: terms.hash,
          locale: terms.locale,
          accepted_at: '2026-07-20T10:00:00.000Z'
        }
      })
    ).toBe(true)
    expect(
      serverHasCurrentAcceptance(terms, {
        terms: {
          version: terms.version,
          content_hash: 'b'.repeat(64),
          locale: terms.locale,
          accepted_at: '2026-07-20T10:00:00.000Z'
        }
      })
    ).toBe(false)
  })

  it('keeps the modal closed while status is loading and after current acceptance', () => {
    expect(INITIAL_CONSENT_MODAL_STATE).toEqual({ status: 'loading', open: false })
    expect(
      resolveConsentModalState(terms, {
        terms: {
          version: terms.version,
          content_hash: terms.hash,
          locale: terms.locale,
          accepted_at: '2026-07-20T10:00:00.000Z'
        }
      })
    ).toEqual({ status: 'accepted', open: false })
  })

  it('keeps missing or stale acceptance silent until message submission', () => {
    expect(resolveConsentModalState(terms, { terms: null })).toEqual({
      status: 'required',
      open: false
    })
  })

  it('opens the modal when message submission requires acceptance', () => {
    expect(requestConsentModalState({ status: 'required', open: false })).toEqual({
      status: 'required',
      open: true
    })
    expect(requestConsentModalState({ status: 'accepted', open: false })).toEqual({
      status: 'accepted',
      open: false
    })
  })
})
