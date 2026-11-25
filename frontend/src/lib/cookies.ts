// Browser only: both read the current page.

export function readCookie(name: string): string | undefined {
  const prefix = `${name}=`
  return document.cookie
    .split('; ')
    .find((cookie) => cookie.startsWith(prefix))
    ?.slice(prefix.length)
}

// Only on https, so cookies still stick on a plain http dev server.
export function secureAttribute(): string {
  return location.protocol === 'https:' ? '; Secure' : ''
}
