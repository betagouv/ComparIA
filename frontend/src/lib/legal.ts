import { resolve } from '$app/paths'
import { m } from '$lib/i18n/messages'

export type LegalLink = { href: string; label: string }

/** The public legal pages, in the order they are listed everywhere. */
export function legalPageLinks(): LegalLink[] {
  return [
    { href: resolve('/donnees-personnelles'), label: m['consent.links.privacy']() },
    { href: resolve('/modalites'), label: m['consent.links.terms']() },
    { href: resolve('/arene/accessibilite'), label: m['footer.links.accessibility']() },
    { href: resolve('/arene/ecoconception'), label: m['footer.links.rgesn']() }
  ]
}
