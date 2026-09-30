import type { ResolvedPathname } from '$app/types'

export type InternalLinkProps = {
  href: ResolvedPathname
}
export type ExternalHref = `https://${string}` | `http://${string}`
export type ExternalLinkProps = {
  href: ExternalHref
  target: '_blank'
  rel: 'noopener external'
}
export type AnyLinkProps = InternalLinkProps | ExternalLinkProps

export function getExternalLinkProps(href: ExternalHref): ExternalLinkProps {
  return { href, target: '_blank', rel: 'noopener external' }
}

export function validExternalUrl(
  href: unknown,
  allowedProtocols: string[] = ['https:']
): ExternalHref | null {
  if (typeof href !== 'string') return null
  try {
    const url = new URL(href)
    return allowedProtocols.includes(url.protocol) ? (url.toString() as ExternalHref) : null
  } catch {
    return null
  }
}

export function validUrl(
  href: unknown,
  allowedProtocols: string[] = ['https:']
): ExternalHref | ResolvedPathname | null {
  if (typeof href !== 'string') return null
  // Only same-site paths: '//evil.example' is a protocol-relative URL, not a path.
  if (href.startsWith('/') && !href.startsWith('//')) return href as ResolvedPathname
  return allowedProtocols.length ? validExternalUrl(href, allowedProtocols) : null
}
