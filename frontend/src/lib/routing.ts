import { resolve } from '$app/paths'
import type { Pathname, ResolvedPathname } from '$app/types'

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

/**
 * The Instance path: the prefix the app is mounted under, '' or e.g. '/fr'.
 * Read from `resolve` so that it is always the one the framework builds links with.
 */
export function instancePath(): string {
  return resolve('/').replace(/\/$/, '')
}

/**
 * A pathname as SvelteKit hands it to hooks and `page.url`, which carries the
 * Instance path, turned back into an app route that `resolve` can be given.
 */
export function withoutInstancePath(pathname: string): Pathname {
  const prefix = instancePath()
  if (!prefix) return pathname as Pathname
  if (pathname === prefix) return '/'
  return (pathname.startsWith(`${prefix}/`) ? pathname.slice(prefix.length) : pathname) as Pathname
}

/**
 * Path attribute of the cookies the frontend sets: the Instance path, so that
 * Instances sharing an origin do not see each other's cookies, or '/' with none.
 */
export function instanceCookiePath(): string {
  return instancePath() || '/'
}
