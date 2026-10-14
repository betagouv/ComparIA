/** A key from a label: lowercase ASCII, words joined by underscores. */
export function toKey(label: string): string {
  return label
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
}

/** The key, with a number added when another tool already uses it. */
export function uniqueKey(base: string, taken: string[]): string {
  const key = base || 'outil'
  if (!taken.includes(key)) return key
  let n = 2
  while (taken.includes(`${key}_${n}`)) n++
  return `${key}_${n}`
}
