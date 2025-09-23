export function sortIfDefined(a: Record<string, any>, b: Record<string, any>, key: string) {
  if (a[key] !== undefined && b[key] !== undefined) return b[key] - a[key]
  if (a[key] !== undefined) return -1
  if (b[key] !== undefined) return 1
  return a.id.localeCompare(b.id)
}
