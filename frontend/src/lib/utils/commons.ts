import { sanitize as gradioSanitize } from '@gradio/sanitize'

export const noop = () => {}

export function sanitize(html: string): string {
  return gradioSanitize(html, '/')
}

export function propsToAttrs(props: Record<string, unknown>): string {
  return Object.entries(props)
    .map(([k, v]) => `${k}="${v}"`)
    .join(' ')
}

export function externalLinkProps(props: Record<string, unknown> | string): string {
  const _props = { target: '_blank', rel: 'noopener external' }
  return propsToAttrs(
    typeof props === 'string' ? { ..._props, href: props } : { ..._props, ...props }
  )
}
