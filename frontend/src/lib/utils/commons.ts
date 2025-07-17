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

export function copyToClipboard(value: string): Promise<void> {
  if ('clipboard' in navigator) {
    return navigator.clipboard.writeText(value)
  } else {
    return new Promise((resolve, reject) => {
      const textArea = document.createElement('textarea')
      textArea.value = value
  
      textArea.style.position = 'absolute'
      textArea.style.left = '-999999px'
  
      document.body.prepend(textArea)
      textArea.select()
  
      try {
        document.execCommand('copy')
        resolve()
      } catch (err) {
        console.error(err)
        reject(err)
      } finally {
        textArea.remove()
      }
    })
  }
}
