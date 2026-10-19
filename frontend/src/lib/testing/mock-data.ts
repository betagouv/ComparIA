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
