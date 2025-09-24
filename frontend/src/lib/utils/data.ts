export function sortIfDefined(a: Record<string, any>, b: Record<string, any>, key: string) {
  if (a[key] !== undefined && b[key] !== undefined) return b[key] - a[key]
  if (a[key] !== undefined) return -1
  if (b[key] !== undefined) return 1
  return a.id.localeCompare(b.id)
}

export function downloadTextFile(data: string, filename: string) {
  const blob = new Blob([data], { type: 'text/csv' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename + '.csv'
  a.click()
}
