import sanitizeHtml from 'sanitize-html'

export const noop = () => {}

export function sanitize(html: string): string {
  return sanitizeHtml(html, {
    allowedAttributes: {
      span: ['class'],
      a: ['href', 'rel', 'target', 'title', 'class'],
      br: []
    }
  })
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

export function shuffleArray<T>(array: T[]): T[] {
  const newArray = [...array]
  for (let i = newArray.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[newArray[i], newArray[j]] = [newArray[j], newArray[i]]
  }
  return newArray
}

// Helper function to select a random item from an array
export function selectRandomFromArray<T>(array: T[]): T | undefined {
  if (!array || array.length === 0) {
    return undefined
  }
  return array[Math.floor(Math.random() * array.length)]
}
