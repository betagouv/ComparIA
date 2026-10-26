import type { AdminLegalDocument } from '$lib/generated/admin'
import type {
  InformationalLegalPageLink,
  InformationalLegalPageLinks
} from '$lib/generated/backend'

export const informationalLegalPageLink = (
  data: Partial<InformationalLegalPageLink> = {}
): Required<InformationalLegalPageLink> => ({
  mode: 'internal',
  external_url: null,
  visible_in_legal_menu: true,
  visible_in_settings: true,
  ...data
})

export const informationalLegalPageLinks: Required<InformationalLegalPageLinks> = {
  legal_notice: informationalLegalPageLink(),
  accessibility: informationalLegalPageLink(),
  ecodesign: informationalLegalPageLink()
}

export const adminLegalDocument = (
  data: Partial<AdminLegalDocument> = {}
): Required<AdminLegalDocument> => ({
  id: '11111111-1111-4111-8111-111111111111',
  kind: 'terms',
  version: '1.0',
  content: { fr: '# Conditions actives' },
  content_hash: 'a'.repeat(64),
  published_at: '2026-07-20T10:00:00.000Z',
  effective_at: '2026-07-20T10:00:00.000Z',
  retired_at: null,
  ...data
})
