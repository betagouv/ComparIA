import sanitizeHtml from 'sanitize-html'

export const noop = () => {}

export function sanitize(html: string): string {
  return sanitizeHtml(html, {
    allowedAttributes: {
      span: ['class'],
      a: ['href', 'rel', 'target', 'title', 'class', 'data-fr-opened', 'aria-controls'],
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

/*
 Try to get translation but do not error out and use default if any
 */
export function tryI18n(key: string, default_?: string): string | undefined {
  try {
    // @ts-expect-error - fallback if error
    return m[`generated.${key}`]()
  } catch (_e) {
    // FIXME throw error?
    return default_
  }
}

// Typescript object helpers

type Key = PropertyKey
type Entry = readonly [Key, any]
type FromEntries<E extends readonly Entry[]> = {
  [P in E[number] as P[0]]: Extract<E[number], readonly [P[0], any]>[1]
}

export function getKeys<T extends Record<Key, any>, K extends (keyof T)[]>(obj: T): K {
  return Object.keys(obj) as K
}

export function toEntries<T extends Record<Key, unknown>>(
  obj: T
): { [K in keyof T]: [K, T[K]] }[keyof T][] {
  return Object.entries(obj) as { [K in keyof T]: [K, T[K]] }[keyof T][]
}

export function fromEntries<const E extends readonly Entry[]>(entries: E): FromEntries<E> {
  return Object.fromEntries(entries as Iterable<readonly [Key, unknown]>) as FromEntries<E>
}

export function pick<T extends Record<Key, any>, K extends keyof T>(
  obj: T,
  keys: readonly K[]
): Pick<T, K> {
  const out = {} as Pick<T, K>
  for (const k of keys) {
    out[k] = obj[k]
  }
  return out
}

export function omit<T extends Record<Key, any>, K extends keyof T>(
  obj: T,
  keys: readonly K[]
): Omit<T, K> {
  const keySet = new Set<Key>(keys as readonly Key[])
  const out: Partial<T> = {}

  for (const [k, v] of Object.entries(obj) as Array<[keyof T, T[keyof T]]>) {
    if (!keySet.has(k as Key)) out[k] = v
  }

  return out as Omit<T, K>
}
